$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Backend = Join-Path $ProjectRoot "backend"

Write-Host "RH Job - instalacao e inicializacao local"
Write-Host "Projeto: $ProjectRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python nao encontrado no PATH. Instale Python 3.11+ e marque Add Python to PATH."
    exit 1
}

if (-not (Test-Path $Python)) {
    Write-Host "Criando ambiente virtual..."
    python -m venv (Join-Path $ProjectRoot ".venv")
}

Write-Host "Instalando dependencias..."
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

function Start-RHJobServer {
    param(
        [int]$Port,
        [string]$LogName
    )

    $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Porta $Port ja esta em uso. Servidor nao sera iniciado nessa porta."
        return
    }

    $stdout = Join-Path $ProjectRoot "$LogName.log"
    $stderr = Join-Path $ProjectRoot "$LogName.err.log"

    Write-Host "Iniciando servidor na porta $Port..."
    Start-Process `
        -FilePath $Python `
        -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port $Port" `
        -WorkingDirectory $Backend `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
}

Start-RHJobServer -Port 8000 -LogName "server-8000"
Start-RHJobServer -Port 8001 -LogName "server-8001"

Write-Host ""
Write-Host "Aplicacao iniciada."
Write-Host "Com login: http://localhost:8000"
Write-Host "Sem login: http://localhost:8001"
Write-Host ""
Write-Host "Login inicial da porta 8000:"
Write-Host "E-mail: admin@rhjob.local"
Write-Host "Senha: admin123"
