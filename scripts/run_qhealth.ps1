[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$BackendPython = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $BackendPython)) {
  throw "Backend virtual environment not found at $BackendPython. Create it first with: py -3.11 -m venv .venv"
}

Start-Process powershell.exe -ArgumentList @(
  '-NoExit',
  '-Command',
  "Set-Location '$Root'; & '$BackendPython' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-access-log"
)

Start-Process powershell.exe -ArgumentList @(
  '-NoExit',
  '-Command',
  "Set-Location '$(Join-Path $Root 'frontend')'; npm run dev -- --host 127.0.0.1"
)

Write-Host 'EntangleX Q-Health started.' -ForegroundColor Green
Write-Host 'Backend:  http://127.0.0.1:8000/api/health'
Write-Host 'Frontend: http://127.0.0.1:5173'
