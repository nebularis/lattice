# SPDX-License-Identifier: MPL-2.0
# Shared helpers of the MSA-I9 probes. Dot-source it: . "$PSScriptRoot\lib.ps1"
# Everything this spike creates in Docker is named msa-i9-*, on the network msa-i9-net, so the cleanup touches nothing else.

$script:Spike = Split-Path -Parent $PSScriptRoot
$script:Net = 'msa-i9-net'
$script:Broker = 'rabbitmq:4-management-alpine'
$script:Runtime = 'eclipse-temurin:25-jre'
$script:Results = Join-Path $Spike 'results'
$script:Utf8 = New-Object System.Text.UTF8Encoding $false
$script:SkewMs = 0

function Invoke-Docker {
    # Native stderr is not turned into a PowerShell error, and the output is returned as lines.
    $ErrorActionPreference = 'Continue'
    $out = & docker @args 2>&1 | ForEach-Object { "$_" }
    return $out
}

function Test-Names {
    param([string]$Filter)
    return @(Invoke-Docker ps -a --filter "name=$Filter" --format '{{.Names}}')
}

function New-Network {
    if (-not (Invoke-Docker network ls --filter "name=^$Net$" --format '{{.Name}}')) {
        Invoke-Docker network create $Net | Out-Null
    }
}

function Start-Node {
    param([int]$N)
    $name = "msa-i9-rmq$N"
    Invoke-Docker run -d --name $name --hostname $name --network $Net --label msa-i9=1 `
        -e 'RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS=-setcookie msa-i9-cookie' -e 'RABBITMQ_CTL_ERL_ARGS=-setcookie msa-i9-cookie' `
        -e "RABBITMQ_NODENAME=rabbit@$name" `
        -v "$(Join-Path $Spike 'config\enabled_plugins'):/etc/rabbitmq/enabled_plugins:ro" `
        -v "$(Join-Path $Spike 'config\msa-i9.conf'):/etc/rabbitmq/conf.d/30-msa-i9.conf:ro" `
        $Broker | Out-Null
}

function Wait-Node {
    param([int]$N, [int]$Seconds = 120)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        $s = Invoke-Docker exec "msa-i9-rmq$N" rabbitmq-diagnostics -q listeners
        if ($LASTEXITCODE -eq 0 -and ($s -join ' ') -match '5552') { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Start-Cluster {
    New-Network
    Start-Node 1
    Start-Node 2
    Start-Node 3
    if (-not (Wait-Node 1)) { throw 'node 1 did not start' }
    if (-not (Wait-Node 2)) { throw 'node 2 did not start' }
    if (-not (Wait-Node 3)) { throw 'node 3 did not start' }
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        $n = (Invoke-Docker exec msa-i9-rmq1 rabbitmqctl eval 'length([node()|nodes()]).') -join ''
        if ($n.Trim() -eq '3') { return }
        Start-Sleep -Seconds 2
    }
    throw 'the three nodes did not form a cluster'
}

function Start-Ctl {
    # A long-lived container for one-shot tasks and for reading the clock the other containers use.
    if (-not (Test-Names 'msa-i9-ctl')) {
        New-Item -ItemType Directory -Force $Results | Out-Null
        Invoke-Docker run -d --name msa-i9-ctl --hostname msa-i9-ctl --network $Net --label msa-i9=1 `
            -v "$(Join-Path $Spike 'target'):/app:ro" -v "${Results}:/out" $Runtime sleep infinity | Out-Null
    }
}

function Invoke-Probe {
    # One-shot task in the control container.
    $out = Invoke-Docker exec msa-i9-ctl java '-Dorg.slf4j.simpleLogger.defaultLogLevel=warn' -jar /app/probes.jar @args
    return $out
}

function Start-Client {
    # A client container: probe mode, id, run directory (below results) and further options. Logs go to /out/<run>/<id>.log.
    param([string]$Run, [string]$Id, [string]$Mode, [string[]]$Options = @(), [string[]]$DockerOptions = @())
    $name = "msa-i9-$Id"
    Invoke-Docker run -d --name $name --hostname $name --network $Net --label msa-i9=1 @DockerOptions `
        -v "$(Join-Path $Spike 'target'):/app:ro" -v "${Results}:/out" $Runtime `
        java '-Xmx256m' '-Dorg.slf4j.simpleLogger.defaultLogLevel=warn' -jar /app/probes.jar $Mode --id $Id --log "/out/$Run/$Id.log" @Options | Out-Null
}

function Set-Skew {
    # The containers read the clock of the Docker VM, the host reads its own. The sample with the shortest round trip wins.
    $best = [long]::MaxValue
    for ($i = 0; $i -lt 7; $i++) {
        $a = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        $ns = (Invoke-Docker exec msa-i9-ctl date +%s%N) -join ''
        $b = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        if (($b - $a) -lt $best) {
            $best = $b - $a
            $script:SkewMs = [long]([decimal]$ns.Trim() / 1000000) - [long](($a + $b) / 2)
        }
    }
    Write-Host "clock skew of the Docker VM against the host: $SkewMs ms, round trip $best ms"
}

function Get-VmNow {
    return [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() + $script:SkewMs
}

function Write-Harness {
    # One line of the harness log, in the clock of the containers.
    param([string]$RunDir, [string]$Event, [string]$Who, [string]$Message = '', [long]$At = 0)
    if ($At -le 0) { $At = Get-VmNow }
    $line = '{"t":' + $At + ',"c":"' + $Who + '","e":"' + $Event + '","msg":"' + $Message + '"}' + "`n"
    [IO.File]::AppendAllText((Join-Path $RunDir 'harness.log'), $line, $Utf8)
    Write-Host ("[{0}] {1} {2} {3}" -f (Get-Date -Format 'HH:mm:ss'), $Event, $Who, $Message)
}

function Write-Text {
    param([string]$Path, [string[]]$Lines)
    [IO.File]::WriteAllText($Path, (($Lines -join "`n") + "`n"), $Utf8)
}

function Count-Matches {
    # How many lines of a log match, 0 for a log not written yet.
    param([string]$Path, [string]$Pattern)
    if (-not (Test-Path $Path)) { return 0 }
    return @(Select-String -Path $Path -Pattern $Pattern -SimpleMatch:$false).Count
}

function Distinct-Partitions {
    # The partitions a consumer log shows a delivery from.
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    $set = @{}
    foreach ($m in (Select-String -Path $Path -Pattern '"e":"rx","s":(\d+)')) { $set[$m.Matches[0].Groups[1].Value] = 1 }
    return $set.Count
}

function Stop-Spike {
    # Remove every container and the network this spike made, and nothing else.
    $names = Test-Names 'msa-i9-'
    foreach ($n in $names) {
        if ($n -like 'msa-i9-*') { Invoke-Docker rm -f -v $n | Out-Null }
    }
    if (Invoke-Docker network ls --filter "name=^$Net$" --format '{{.Name}}') { Invoke-Docker network rm $Net | Out-Null }
}

function Run-Analysis {
    param([string]$RunDir, [int]$Partitions = 8, [string]$Resume = '')
    $java = Join-Path (& mise where java) 'bin\java.exe'
    $a = @('-jar', (Join-Path $Spike 'target\probes.jar'), 'analyze', '--dir', $RunDir, '--partitions', $Partitions, '--out', (Join-Path $RunDir 'analysis.txt'))
    if ($Resume) { $a += @('--resume', $Resume) }
    & $java @a
}

function Remove-Clients {
    # Remove the named client containers of a run, whatever their state.
    param([string[]]$Ids)
    foreach ($i in $Ids) {
        if (Test-Names "^msa-i9-$i$") { Invoke-Docker rm -f -v "msa-i9-$i" | Out-Null }
    }
}

function Copy-ContainerLogs {
    # The container's own stdout and stderr, which show what the client library printed besides the probe's log lines.
    param([string]$RunDir, [string[]]$Ids)
    foreach ($i in $Ids) {
        if (Test-Names "^msa-i9-$i$") {
            $text = Invoke-Docker logs "msa-i9-$i"
            $keep = @($text | Where-Object { $_ -notmatch '^\{"t":' })
            $pick = @($keep | Where-Object { $_ -match 'Stored offset|consumer update|Consumer update|No stored offset|Looking up' })
            if ($pick.Count -gt 0) { $keep = $pick }
            if ($keep.Count -gt 0) { Write-Text (Join-Path $RunDir "$i.container.txt") ($keep | Select-Object -First 80) }
        }
    }
}

function Compress-Logs {
    # Gzip the raw probe logs of a run once they are analysed, and keep the small files as they are.
    param([string]$RunDir, [long]$MinBytes = 200000)
    foreach ($f in Get-ChildItem $RunDir -Filter '*.log') {
        if ($f.Length -lt $MinBytes) { continue }
        $src = [IO.File]::OpenRead($f.FullName)
        $dst = [IO.File]::Create($f.FullName + '.gz')
        $gz = New-Object IO.Compression.GZipStream($dst, [IO.Compression.CompressionMode]::Compress)
        $src.CopyTo($gz)
        $gz.Dispose(); $dst.Dispose(); $src.Dispose()
        Remove-Item $f.FullName
    }
}

function Wait-Until {
    # Poll a script block until it returns true, or give up after the timeout. Returns whether it became true.
    param([scriptblock]$Test, [int]$Seconds, [int]$Every = 1)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Test) { return $true }
        Start-Sleep -Seconds $Every
    }
    return $false
}

function New-SuperStream {
    param([string]$Name, [int]$Partitions = 8, [switch]$Spread)
    Invoke-Probe delete --super $Name --partitions $Partitions | Out-Null
    if ($Spread) {
        Invoke-Probe declare --super $Name --partitions $Partitions --spread true | Out-Null
    } else {
        Invoke-Probe declare --super $Name --partitions $Partitions | Out-Null
    }
}

function Get-GroupView {
    # The broker's view of the SAC groups of a super stream: for each partition the active consumer's connection.
    param([string]$Super, [int]$Partitions = 8)
    $rows = @()
    for ($i = 0; $i -lt $Partitions; $i++) {
        $out = Invoke-Docker exec msa-i9-rmq1 rabbitmq-streams -q list_stream_group_consumers --stream "$Super-$i" --reference lattice.studio.writers connection_name state
        foreach ($l in $out) {
            if ($l -match '^\S' -and $l -notmatch 'connection_name|Error|error') { $rows += "p$i`t$l" }
        }
    }
    return $rows
}
