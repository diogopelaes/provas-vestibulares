<#
===============================================================================
ARQUIVO: start_app.ps1
CAMADA: Automação / Inicializador do Servidor e Aplicação
PAPEL NO SISTEMA:
  1. Cria o ambiente virtual (.venv) se não existir.
  2. Atualiza o pip e instala os requirements (se houver requirements.txt).
  3. Detecta porta livre (iniciando em 8000).
  4. Executa o servidor em outro terminal independente.
  5. Aguarda o servidor responder e abre o navegador no index.
===============================================================================
#>

[CmdletBinding()]
param (
    [int]$PortaInicial = 8000
)

$ErrorActionPreference = "Stop"

$rootDir = $PSScriptRoot
$appDir = Join-Path $rootDir "app"
$serverScript = Join-Path $appDir "server.py"
$venvDir = Join-Path $rootDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      Iniciando Central de Provas de Vestibulares        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. Verificar / Criar o Ambiente Virtual (.venv)
# -----------------------------------------------------------------------------
function Test-PythonExe([string]$path) {
    if ([string]::IsNullOrWhiteSpace($path)) { return $false }
    if (-not (Test-Path $path)) { return $false }
    try {
        $output = & $path --version 2>&1
        return ($LASTEXITCODE -eq 0 -or $output -match "Python")
    } catch {
        return $false
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Host "`n[.venv] Ambiente virtual não encontrado. Criando em: $venvDir..." -ForegroundColor Cyan

    $candidatos = @(
        "C:\Users\Diogo\AppData\Local\Python\pythoncore-3.14-64\python.exe",
        (Get-Command python.exe -ErrorAction SilentlyContinue).Source,
        (Get-Command py.exe -ErrorAction SilentlyContinue).Source,
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python314\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe"
    )

    $basePython = $null
    foreach ($cand in $candidatos) {
        if (Test-PythonExe $cand) {
            $basePython = $cand
            break
        }
    }

    while ($null -eq $basePython) {
        Write-Host "`n[Python] Informe o caminho completo do executável python.exe:" -ForegroundColor Yellow
        $entrada = Read-Host "Caminho do python.exe (ou 'sair' para cancelar)"
        $entrada = $entrada.Trim().Trim('"').Trim("'")

        if ($entrada -eq "sair" -or [string]::IsNullOrWhiteSpace($entrada)) {
            Write-Host "`n[Cancelado] Operação cancelada pelo usuário." -ForegroundColor Red
            exit 1
        }

        if (Test-PythonExe $entrada) {
            $basePython = $entrada
        } else {
            Write-Host "[Erro] Caminho inválido. Tente novamente." -ForegroundColor Red
        }
    }

    try {
        & $basePython -m venv $venvDir
        if (-not (Test-Path $venvPython)) {
            throw "Falha ao criar o arquivo $venvPython."
        }
        Write-Host "[.venv] Ambiente virtual criado com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "[Erro Crítico] Falha ao criar ambiente virtual: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[Python] Ambiente virtual detectado: .venv" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# 2. Atualizar pip e instalar dependências no .venv
# -----------------------------------------------------------------------------
$reqPath = Join-Path $rootDir "requirements.txt"
if (Test-Path $reqPath) {
    Write-Host "[pip] Garantindo dependências no .venv..." -ForegroundColor Cyan
    try {
        & $venvPython -m pip install -r $reqPath --quiet
        Write-Host "[pip] Dependências verificadas com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "[Aviso] Falha ao executar pip: $_" -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------------------
# 3. Verificar / Inicializar Índice de Busca nos PDFs
# -----------------------------------------------------------------------------
$dbPath = Join-Path $appDir ".search_cache.db"
$buscaScript = Join-Path $appDir "busca.py"
if (-not (Test-Path $dbPath)) {
    Write-Host "[Busca] Banco de busca não encontrado. Criando índice inicial dos PDFs..." -ForegroundColor Cyan
    try {
        & $venvPython $buscaScript --indexar
    } catch {
        Write-Host "[Aviso] Erro na indexação inicial: $_" -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------------------
# 4. Varredura de Portas Disponíveis (Inicia em 8000)
# -----------------------------------------------------------------------------
function Test-PortInUse([int]$port) {
    $tcp = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($null -ne $tcp) { return $true }
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        $listener.Stop()
        return $false
    } catch {
        return $true
    }
}

function Test-ServerResponding([int]$port) {
    try {
        $request = [System.Net.WebRequest]::Create("http://127.0.0.1:$port/api/vestibulares")
        $request.Timeout = 1000
        $response = $request.GetResponse()
        $response.Close()
        return $true
    } catch {
        return $false
    }
}

$porta = $PortaInicial
while ($porta -lt ($PortaInicial + 100)) {
    if (Test-ServerResponding $porta) {
        $url = "http://localhost:$porta"
        Write-Host "[Servidor] O servidor já está ativo e respondendo na porta $porta!" -ForegroundColor Green
        Write-Host "[Navegador] Abrindo $url no navegador..." -ForegroundColor Cyan
        Start-Process $url
        exit 0
    }
    if (-not (Test-PortInUse $porta)) {
        break
    }
    Write-Host "[Porta] Porta $porta em uso. Verificando $( $porta + 1 )..." -ForegroundColor DarkYellow
    $porta++
}

$url = "http://localhost:$porta"
Write-Host "[Servidor] Porta selecionada: $porta" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 5. Executar o Servidor em Outro Terminal
# -----------------------------------------------------------------------------
Write-Host "[Servidor] Iniciando servidor em novo terminal..." -ForegroundColor Cyan

$serverScriptBlock = @"
`$host.UI.RawUI.WindowTitle = 'Provas de Vestibulares (Porta $porta)'
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '      Servidor Ativo - Provas de Vestibulares            ' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host 'URL Local: $url' -ForegroundColor Green
Write-Host 'Pressione Ctrl+C para encerrar o servidor local.`n' -ForegroundColor Gray
try {
    & '$venvPython' '$serverScript' $porta
} catch {
    Write-Host "`n[Erro no Servidor] `$_" -ForegroundColor Red
} finally {
    Write-Host "`n[Servidor encerrado]" -ForegroundColor Yellow
}
"@

$bytes = [System.Text.Encoding]::Unicode.GetBytes($serverScriptBlock)
$encodedCommand = [Convert]::ToBase64String($bytes)

Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedCommand `
    -WorkingDirectory $rootDir

# -----------------------------------------------------------------------------
# 6. Aguardar Servidor Responder e Abrir Navegador
# -----------------------------------------------------------------------------
Write-Host "[Servidor] Aguardando o servidor responder em $url..." -ForegroundColor Cyan
$tentativas = 0
$maxTentativas = 40
$servidorPronto = $false

while ($tentativas -lt $maxTentativas) {
    Start-Sleep -Milliseconds 250
    $tentativas++
    if (Test-ServerResponding $porta) {
        $servidorPronto = $true
        break
    }
}

if ($servidorPronto) {
    Write-Host "[Servidor] Servidor respondendo com sucesso!" -ForegroundColor Green
} else {
    Write-Host "[Aviso] Tempo limite de espera atingido, tentando abrir navegador..." -ForegroundColor Yellow
}

Write-Host "[Navegador] Abrindo $url no navegador..." -ForegroundColor Cyan
Start-Process $url

Write-Host "`n[Sucesso] Aplicação iniciada com sucesso.`n" -ForegroundColor Green
