$ErrorActionPreference = "Stop"
$gatewayDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Join-Path $env:USERPROFILE "MiMo-API-Compat-Fix"
$settingsPath = Join-Path $env:USERPROFILE ".claude\settings.json"
$python = Get-Command python -ErrorAction Stop

if (-not (Test-Path $settingsPath)) {
    throw "Missing Claude settings file: $settingsPath"
}

$settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
if (-not $settings.api_key) {
    throw "Missing api_key in $settingsPath"
}

$env:MIMO_API_KEY = $settings.api_key
$env:MIMO_API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
$env:MIMO_PROXY_HOST = "127.0.0.1"
$env:MIMO_PROXY_PORT = "15721"
$env:MIMO_CACHE_FILE = Join-Path $gatewayDir "reasoning_cache.json"
$env:MIMO_LOG_FILE = Join-Path $gatewayDir "mimo-compat-proxy.log"

Set-Location $repoDir

while ($true) {
    $proc = Start-Process `
        -FilePath $python.Source `
        -ArgumentList @("$repoDir\proxy\server.py", "--host", "127.0.0.1", "--port", "15721") `
        -WorkingDirectory $repoDir `
        -WindowStyle Hidden `
        -PassThru

    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 8

        try {
            Invoke-RestMethod `
                -Uri "http://127.0.0.1:15721/health" `
                -Headers @{"x-api-key" = "LOCAL_MIMO_COMPAT"} `
                -TimeoutSec 3 | Out-Null
        } catch {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            break
        }
    }

    Start-Sleep -Seconds 2
}
