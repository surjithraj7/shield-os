param(
    [int]$Port = 8000,
    [string]$HostAddr = "0.0.0.0",
    [switch]$Rebuild,
    [string]$LogDir = (Join-Path $PSScriptRoot "logs")
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot "frontend\dist\index.html"))) {
    Write-Host "[deploy] frontend/dist missing - building..." -ForegroundColor Yellow
    $Rebuild = $true
}

if ($Rebuild) {
    Push-Location (Join-Path $RepoRoot "frontend")
    try {
        npm.cmd run build
        if (-not $?) { throw "frontend build failed" }
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Out = Join-Path $LogDir "server_$Port.out.log"
$Err = Join-Path $LogDir "server_$Port.err.log"
$PidFile = Join-Path $LogDir "server_$Port.pid"

Write-Host "[deploy] launching uvicorn on $HostAddr`:$Port" -ForegroundColor Cyan
Write-Host "[deploy] logs: $Out / $Err" -ForegroundColor Cyan

$proc = Start-Process -FilePath "python" -ArgumentList @(
    "-m", "uvicorn", "app.main:app",
    "--host", $HostAddr,
    "--port", $Port
) -WorkingDirectory $RepoRoot -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru -WindowStyle Hidden

$proc.Id | Out-File -FilePath $PidFile -Encoding ascii
Write-Host "[deploy] started PID $($proc.Id) -> http://$HostAddr`:$Port" -ForegroundColor Green
