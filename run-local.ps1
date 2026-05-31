<#
.SYNOPSIS
  Start the Client Intelligence Agent for local development.
  Launches backend (uvicorn + hot reload) and frontend (Vite) in separate terminal windows.

.EXAMPLE
  .\run-local.ps1
#>

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot

# ── Prerequisite checks ───────────────────────────────────────────────────────
foreach ($cmd in 'python', 'node', 'npm') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "$cmd not found in PATH. Install it and retry."
    }
}

# ── Load .env ─────────────────────────────────────────────────────────────────
$EnvFile = Join-Path $Root '.env'
if (-not (Test-Path $EnvFile)) {
    Write-Error ".env not found. Copy .env.example to .env and fill in values."
}

$EnvVars = @{}
foreach ($line in Get-Content $EnvFile) {
    if ($line -match '^([^#\s][^=]*)=(.*)$') {
        $key = $Matches[1].Trim()
        $val = $Matches[2].Trim()
        $EnvVars[$key] = $val
        Set-Item -Path "env:$key" -Value $val
    }
}

$BackendPort = if ($EnvVars['BACKEND_PORT']) { $EnvVars['BACKEND_PORT'] } else { '8000' }

# ── Write frontend/.env.local ─────────────────────────────────────────────────
@(
    "VITE_ENTRA_CLIENT_ID=$($EnvVars['ENTRA_CLIENT_ID'])"
    "VITE_ENTRA_TENANT_ID=$($EnvVars['ENTRA_TENANT_ID'])"
    "VITE_BACKEND_URL=http://localhost:$BackendPort"
    "VITE_LOCAL_MODE=$($EnvVars['LOCAL_MODE'] ?? 'false')"
) | Set-Content (Join-Path $Root 'frontend\.env.local') -Encoding UTF8

# ── Python venv ───────────────────────────────────────────────────────────────
$VenvDir    = Join-Path $Root 'backend\.venv'
$PipExe     = Join-Path $VenvDir 'Scripts\pip.exe'
$UvicornExe = Join-Path $VenvDir 'Scripts\uvicorn.exe'
$ReqFile    = Join-Path $Root 'backend\requirements.txt'
$StampFile  = Join-Path $VenvDir '.req.stamp'

if (-not (Test-Path (Join-Path $VenvDir 'Scripts\python.exe'))) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv $VenvDir
}

$ReqHash = (Get-FileHash $ReqFile -Algorithm MD5).Hash
if (-not (Test-Path $StampFile) -or (Get-Content $StampFile -Raw).Trim() -ne $ReqHash) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
    & $PipExe install -r $ReqFile -q
    Set-Content $StampFile -Value $ReqHash -Encoding UTF8
}

# ── npm install ───────────────────────────────────────────────────────────────
if (-not (Test-Path (Join-Path $Root 'frontend\node_modules'))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location (Join-Path $Root 'frontend')
    npm install --silent
    Pop-Location
}

# ── Launch backend ────────────────────────────────────────────────────────────
$BackendCmd = "`$env:PYTHONPATH = '$Root\backend'; & '$UvicornExe' app.main:app --reload --host 127.0.0.1 --port $BackendPort"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $BackendCmd -WorkingDirectory $Root

# ── Launch frontend ───────────────────────────────────────────────────────────
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'npm run dev' `
    -WorkingDirectory (Join-Path $Root 'frontend')

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Services starting in separate windows." -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:$BackendPort"
Write-Host "  API docs: http://localhost:$BackendPort/docs"
Write-Host ""
Write-Host "Close those windows to stop the services." -ForegroundColor DarkGray
