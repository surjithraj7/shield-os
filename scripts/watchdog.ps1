# watchdog.ps1 - Persistent watchdog for server + cloudflare tunnel
# Run with: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\watchdog.ps1

$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$LogFile  = Join-Path $RepoRoot "logs\watchdog.log"
$ServerPidFile = Join-Path $RepoRoot "logs\server_8000.pid"
$TunnelPidFile = Join-Path $RepoRoot "logs\tunnel.pid"
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
$Cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

$ServerHost = "0.0.0.0"
$ServerPort = 8000
$TunnelUrl  = "http://127.0.0.1:8000"
$HealthUrl  = "http://127.0.0.1:8000/api/health"
$HealthTimeoutSec = 8

function Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$ts  $msg"
    Write-Host $line -ForegroundColor Gray
    $line | Out-File -FilePath $LogFile -Append -Encoding ascii
}

function IsProcessAlive($pidPath) {
    if (!(Test-Path $pidPath)) { return $false }
    $id = (Get-Content $pidPath -ErrorAction SilentlyContinue).Trim()
    if ([int]::TryParse($id, [ref]$null) -and (Get-Process -Id ([int]$id) -ErrorAction SilentlyContinue)) {
        return $true
    }
    return $false
}

function Start-Server {
    Log "STARTING SERVER on $ServerHost`:$ServerPort ..."
    Remove-Item $ServerPidFile -Force -ErrorAction SilentlyContinue
    $outLog = Join-Path $RepoRoot "logs\server_8000.out.log"
    $errLog = Join-Path $RepoRoot "logs\server_8000.err.log"
    $proc = Start-Process -FilePath $Python -ArgumentList @(
        "-m", "uvicorn", "app.main:app",
        "--host", $ServerHost,
        "--port", $ServerPort
    ) -WorkingDirectory $RepoRoot -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath $ServerPidFile -Encoding ascii
    Log "SERVER started PID $($proc.Id)"
    Start-Sleep -Seconds 2
}

function Start-Tunnel {
    Log "STARTING CLOUDFLARE TUNNEL -> $TunnelUrl ..."
    Remove-Item $TunnelPidFile -Force -ErrorAction SilentlyContinue
    $tunOut = Join-Path $RepoRoot "logs\tunnel.out.log"
    $tunErr = Join-Path $RepoRoot "logs\tunnel.err.log"
    $proc = Start-Process -FilePath $Cloudflared -ArgumentList @(
        "tunnel", "--url", $TunnelUrl, "--no-autoupdate"
    ) -WorkingDirectory $RepoRoot -RedirectStandardOutput $tunOut -RedirectStandardError $tunErr -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath $TunnelPidFile -Encoding ascii
    Log "TUNNEL started PID $($proc.Id)"
}

function Stop-Stale($pidPath, $label) {
    if (!(Test-Path $pidPath)) { return }
    $id = (Get-Content $pidPath -ErrorAction SilentlyContinue).Trim()
    if ([int]::TryParse($id, [ref]$null)) {
        $p = Get-Process -Id ([int]$id) -ErrorAction SilentlyContinue
        if ($p) {
            Log "STOPPING stale $label (PID $id)..."
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    Remove-Item $pidPath -Force -ErrorAction SilentlyContinue
}

function Test-ServerHealth {
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec $HealthTimeoutSec -UseBasicParsing -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Get-TunnelUrl {
    $errLog = Join-Path $RepoRoot "logs\tunnel.err.log"
    if (!(Test-Path $errLog)) { return $null }
    $lines = Get-Content $errLog -Tail 20 -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            return $Matches[0]
        }
    }
    return $null
}

# ─── MAIN LOOP ───────────────────────────────────────────────

Log "========== WATCHDOG STARTED =========="

while ($true) {
    # ── Server ──────────────────────────────────────────────
    $serverAlive = Test-ServerHealth
    if ($serverAlive) {
        # Server responds, keep going
    } else {
        # Server down or unhealthy - restart it
        Stop-Stale $ServerPidFile "server"
        Stop-Stale $TunnelPidFile "tunnel"
        Start-Server

        # Wait for server to become healthy
        $waited = 0
        $maxWait = 15
        while ($waited -lt $maxWait -and !(Test-ServerHealth)) {
            Start-Sleep -Seconds 1
            $waited++
        }
        if (Test-ServerHealth) {
            Log "SERVER healthy after ${waited}s"
        } else {
            Log "WARNING: server not healthy after ${maxWait}s"
        }

        # Restart tunnel too
        Stop-Stale $TunnelPidFile "tunnel"
        Start-Tunnel
        Log "WAITING 10s for tunnel URL..."
        Start-Sleep -Seconds 10
        $url = Get-TunnelUrl
        if ($url) {
            Log "TUNNEL URL: $url"
        } else {
            Log "WARNING: tunnel URL not captured yet"
        }
    }

    # ── Tunnel ──────────────────────────────────────────────
    if ($serverAlive) {
        # Only check tunnel if server is fine
        if (!(IsProcessAlive $TunnelPidFile)) {
            Log "TUNNEL process dead - restarting..."
            Stop-Stale $TunnelPidFile "tunnel"
            Start-Tunnel
            Log "WAITING 10s for tunnel URL..."
            Start-Sleep -Seconds 10
            $url = Get-TunnelUrl
            if ($url) {
                Log "TUNNEL URL: $url"
            }
        }
    }

    Start-Sleep -Seconds 15
}
