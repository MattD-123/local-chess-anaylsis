param(
    [switch]$ForceInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$configPath = Join-Path $repoRoot "config.yaml"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

Write-Host "Repo root: $repoRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not available on PATH."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not installed or not available on PATH."
}

if (-not (Test-Path $configPath)) {
    throw "config.yaml not found at $configPath"
}

$configText = Get-Content $configPath -Raw

$pathMatch = [regex]::Match($configText, "(?m)^(\s*path:\s*)(.+)$")
$modelMatch = [regex]::Match($configText, "(?m)^(\s*model:\s*)(.+)$")

if (-not $pathMatch.Success -or -not $modelMatch.Success) {
    throw "Could not find engine path/model fields in config.yaml"
}

$currentEnginePath = $pathMatch.Groups[2].Value.Trim().Trim("'`"")
$currentModel = $modelMatch.Groups[2].Value.Trim().Trim("'`"")

Write-Host ""
Write-Host "Configuration (press Enter to keep current value)"
$enginePathInput = Read-Host "Stockfish path [$currentEnginePath]"
if ([string]::IsNullOrWhiteSpace($enginePathInput)) {
    $enginePathInput = $currentEnginePath
}

if (-not (Test-Path $enginePathInput)) {
    $continueWithoutPathValidation = Read-Host "Path not found: $enginePathInput. Continue anyway? (y/N)"
    if ($continueWithoutPathValidation.ToLower() -ne "y") {
        throw "Aborted due to invalid Stockfish path."
    }
}

$modelInput = Read-Host "Ollama model [$currentModel]"
if ([string]::IsNullOrWhiteSpace($modelInput)) {
    $modelInput = $currentModel
}

$updatedText = [regex]::Replace(
    $configText,
    "(?m)^(\s*path:\s*)(.+)$",
    {
        param($m)
        return $m.Groups[1].Value + $enginePathInput
    },
    1
)

$updatedText = [regex]::Replace(
    $updatedText,
    "(?m)^(\s*model:\s*)(.+)$",
    {
        param($m)
        return $m.Groups[1].Value + $modelInput
    },
    1
)

if ($updatedText -ne $configText) {
    Set-Content -Path $configPath -Value $updatedText -NoNewline
    Write-Host "Updated config.yaml with selected engine path and model."
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
