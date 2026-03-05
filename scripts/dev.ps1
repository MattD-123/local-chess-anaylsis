param(
    [switch]$ForceInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

Write-Host "Repo root: $repoRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not available on PATH."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not installed or not available on PATH."
}

if ($ForceInstall -or -not (Test-Path $venvPython)) {
    Write-Host "Setting up backend virtual environment..."
    Push-Location $backendDir
    try {
        python -m venv .venv
        & $venvPython -m pip install --upgrade pip
        & $venvPython -m pip install -r requirements.txt -r requirements-dev.txt
    } finally {
        Pop-Location
    }
}

if ($ForceInstall -or -not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontendDir
    try {
        npm install
    } finally {
        Pop-Location
    }
}

$backendCmd = "Set-Location '$backendDir'; .\.venv\Scripts\python -m uvicorn main:app --reload --port 8000"
$frontendCmd = "Set-Location '$frontendDir'; npm run dev"

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null

Write-Host "Starting frontend on http://localhost:5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

Write-Host "Done. Open http://localhost:5173 in your browser."
