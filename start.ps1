$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $Python)) {
    python -m venv .venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

New-Item -ItemType Directory -Force -Path data, logs, uploads | Out-Null

$Port = if ($env:PORT) { $env:PORT } else { "8000" }
& $Python -m uvicorn backend.main:app --host 0.0.0.0 --port $Port
