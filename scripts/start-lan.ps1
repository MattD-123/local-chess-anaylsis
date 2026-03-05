$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Backend virtual environment not found. Run .\scripts\dev.ps1 first."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not available on PATH."
}

Write-Host "Building frontend for static hosting..."
Push-Location $frontendDir
try {
    npm run build
} finally {
    Pop-Location
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $ip) {
    $ip = "your-host-ip"
}

Write-Host ""
Write-Host "LAN URL: http://$ip:8000"
Write-Host "Ensure Windows Firewall allows inbound TCP 8000."
Write-Host ""

Push-Location $backendDir
try {
    & $venvPython -m uvicorn main:app --host 0.0.0.0 --port 8000
} finally {
    Pop-Location
}
