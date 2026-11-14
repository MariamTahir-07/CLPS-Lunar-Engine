# Dev start on Windows. From the project root run:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run-dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = if ($env:PORT) { $env:PORT } else { "10000" }
$py = "$root\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv "$root\.venv" }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { python -m venv "$root\.venv" }
  else { throw "Python 3.11+ not found. Install it from python.org and tick 'Add python.exe to PATH'." }
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Node.js 20+ (LTS) not found. Install it from nodejs.org." }
& $py -m pip install -r "$root\backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
if (-not (Test-Path "$root\frontend\node_modules")) {
  Push-Location "$root\frontend"
  npm.cmd ci
  $code = $LASTEXITCODE
  Pop-Location
  if ($code -ne 0) { throw "npm ci failed" }
}
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$root\backend'; & '$py' -m uvicorn app.main:app --port $port"
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$root\frontend'; npm.cmd run dev"
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
  try { Invoke-RestMethod "http://localhost:$port/api/health" -TimeoutSec 2 | Out-Null; $ok = $true } catch { Start-Sleep -Seconds 1 }
}
if ($ok) { Write-Host "Backend healthy on port $port. Opening http://localhost:5173"; Start-Process "http://localhost:5173" }
else { Write-Warning "Backend did not answer on :$port within 30 s - check the backend window for errors." }
