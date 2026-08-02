Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot 'out\local_runtime'
$envFile = Join-Path $projectRoot '.env'
$pythonExe = 'C:\Users\avihu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$instanceRoot = 'C:\Users\avihu\.Neo4jDesktop2\Data\dbmss\dbms-07f6d302-9c7c-4f1f-95bf-201f9ebf8e9a'
$neo4jBat = Join-Path $instanceRoot 'bin\neo4j.bat'
$neo4jPidFile = Join-Path $instanceRoot 'run\neo4j-relate.pid'
$javaHome = 'C:\Users\avihu\.Neo4jDesktop2\Cache\runtime\zulu21.50.19-ca-jre21.0.11-win_x64'
$qaPidFile = Join-Path $runtimeDir 'local_qa.pid'
$runtimeStatusFile = Join-Path $runtimeDir 'runtime_status.json'
$qaUrl = 'http://127.0.0.1:8765'

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

foreach ($requiredPath in @($envFile, $pythonExe, $neo4jBat, $javaHome)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required local runtime component is missing: $requiredPath"
    }
}

if (-not (Select-String -LiteralPath $envFile -Pattern '^NEO4J_PASSWORD=.+$' -Quiet)) {
    throw 'NEO4J_PASSWORD is not configured.'
}

function Test-LocalPort {
    param([Parameter(Mandatory = $true)][int]$Port)
    return [bool](netstat -ano |
        Select-String -Pattern "^\s*TCP\s+127\.0\.0\.1:$Port\s+.*LISTENING\s+\d+\s*$" |
        Select-Object -First 1)
}

function Wait-LocalPort {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort -Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Start-ContainedChild {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Failed to start local child process: $FilePath"
    }
    return $process
}

$systemRoot = [Environment]::GetEnvironmentVariable('SystemRoot')

$neo4jStartedByLauncher = $false
if (-not (Test-LocalPort -Port 7687)) {
    $commandInterpreter = Join-Path $systemRoot 'System32\cmd.exe'
    # Neo4j mode: 'console'
    $neo4jCommand = 'set "JAVA_HOME={0}" && set "PATH={0}\bin;{1}\System32" && call "{2}" console' -f $javaHome, $systemRoot, $neo4jBat
    $neo4jArguments = '/d /s /c "{0}"' -f $neo4jCommand
    $neo4jProcess = Start-ContainedChild `
        -FilePath $commandInterpreter `
        -Arguments $neo4jArguments `
        -WorkingDirectory $instanceRoot
    [System.IO.File]::WriteAllText(
        $neo4jPidFile,
        [string]$neo4jProcess.Id,
        [System.Text.UTF8Encoding]::new($false)
    )
    $neo4jStartedByLauncher = $true
    if (-not (Wait-LocalPort -Port 7687 -TimeoutSeconds 45)) {
        throw 'Neo4j did not become ready within 45 seconds.'
    }
}

$qaHealthy = $false
try {
    $health = Invoke-RestMethod -Uri "$qaUrl/api/health" -TimeoutSec 2
    $qaHealthy = $health.status -eq 'ok'
} catch {
    $qaHealthy = $false
}

$qaProcessId = $null
if (-not $qaHealthy) {
    $qaScript = Join-Path $projectRoot 'local_qa_app.py'
    $qaProcess = Start-ContainedChild `
        -FilePath $pythonExe `
        -Arguments "`"$qaScript`"" `
        -WorkingDirectory $projectRoot
    $qaProcessId = $qaProcess.Id
    [System.IO.File]::WriteAllText(
        $qaPidFile,
        [string]$qaProcessId,
        [System.Text.UTF8Encoding]::new($false)
    )
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "$qaUrl/api/health" -TimeoutSec 2
            if ($health.status -eq 'ok' -and $health.neo4j_running) {
                $qaHealthy = $true
                break
            }
        } catch {
            $qaHealthy = $false
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $qaHealthy) {
    throw 'The local Q&A application did not become healthy.'
}
if ($null -eq $qaProcessId -and (Test-Path -LiteralPath $qaPidFile)) {
    $qaProcessId = (Get-Content -LiteralPath $qaPidFile -Raw).Trim()
}

$status = [ordered]@{
    status = 'PASS_LOCAL_SYSTEM_RUNNING'
    timestamp = (Get-Date).ToString('o')
    neo4j_running = (Test-LocalPort -Port 7687)
    neo4j_started_by_launcher = $neo4jStartedByLauncher
    qa_running = $qaHealthy
    qa_process_id = $qaProcessId
    ui_url = $qaUrl
    mode = 'D4_CANONICAL_LOCAL_READ_ONLY'
}
$statusJson = $status | ConvertTo-Json
[System.IO.File]::WriteAllText(
    $runtimeStatusFile,
    $statusJson,
    [System.Text.UTF8Encoding]::new($false)
)
$statusJson
