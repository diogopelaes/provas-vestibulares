<#
===============================================================================
ARQUIVO: app/start_app.ps1
CAMADA: Automação / Script de Inicialização (PowerShell)
PAPEL NO SISTEMA:
  - Inicializador completo e autônomo da aplicação local:
      1. Verifica se o ambiente virtual (.venv) existe na raiz do projeto.
      2. Se não existir, busca o Python base (ou solicita interativamente ao usuário),
         cria o .venv e atualiza o pip.
      3. Realiza varredura de portas livres a partir de 8000.
      4. Abre um NOVO terminal independente para executar o servidor (app\server.py).
      5. Aguarda o servidor estar pronto e abre a aplicação no navegador padrão.
===============================================================================
#>

[CmdletBinding()]
param (
    [int]$PortaInicial = 8000
)

$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
$rootDir = (Resolve-Path "$scriptDir\..").Path
$venvDir = "$rootDir\.venv"
$venvPython = "$venvDir\Scripts\python.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      Iniciando Central de Provas de Vestibulares        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# Função auxiliar: Testa se um executável Python responde corretamente
# -----------------------------------------------------------------------------
function Test-PythonExecutable([string]$path) {
    if ([string]::IsNullOrWhiteSpace($path)) { return $false }
    if (-not (Test-Path $path)) { return $false }
    try {
        $output = & $path --version 2>&1
        return ($LASTEXITCODE -eq 0 -or $output -match "Python")
    } catch {
        return $false
    }
}

# -----------------------------------------------------------------------------
# 1. Verificar / Criar o Ambiente Virtual (.venv)
# -----------------------------------------------------------------------------
if (-not (Test-Path $venvPython)) {
    Write-Host "`n[Aviso] Ambiente virtual (.venv) não encontrado em $venvDir." -ForegroundColor Yellow
    Write-Host "[.venv] Preparando criação automática do ambiente virtual..." -ForegroundColor Cyan

    # Candidatos a interpretador base
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
        if (Test-PythonExecutable $cand) {
            $basePython = $cand
            break
        }
    }

    # Se nenhum Python for encontrado automaticamente, solicita interativamente ao usuário
    while ($null -eq $basePython) {
        Write-Host "`n==========================================================" -ForegroundColor Red
        Write-Host " [ATENÇÃO] O Python não foi encontrado automaticamente!" -ForegroundColor Red
        Write-Host "==========================================================" -ForegroundColor Red
        Write-Host "Para criar o ambiente virtual e iniciar a aplicação," -ForegroundColor Yellow
        Write-Host "por favor informe o caminho completo do executável python.exe." -ForegroundColor Yellow
        Write-Host "(Exemplo: C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python314\python.exe)`n" -ForegroundColor Gray

        $entrada = Read-Host "Digite o caminho do python.exe (ou 'sair' para cancelar)"
        $entrada = $entrada.Trim().Trim('"').Trim("'")

        if ($entrada -eq "sair" -or [string]::IsNullOrWhiteSpace($entrada)) {
            Write-Host "`n[Cancelado] Operação cancelada pelo usuário." -ForegroundColor Red
            Read-Host "Pressione Enter para fechar..."
            exit 1
        }

        if (Test-PythonExecutable $entrada) {
            $basePython = $entrada
            Write-Host "`n[Sucesso] Interpretador Python validado: $basePython" -ForegroundColor Green
        } else {
            Write-Host "`n[Erro] O caminho informado não é um executável Python válido ou não foi encontrado." -ForegroundColor Red
            Write-Host "Tente novamente ou verifique se o caminho digitado está correto." -ForegroundColor DarkYellow
        }
    }

    Write-Host "[.venv] Criando ambiente virtual em: $venvDir..." -ForegroundColor Cyan
    try {
        & $basePython -m venv $venvDir
        if (-not (Test-Path $venvPython)) {
            throw "O arquivo $venvPython não foi gerado após a execução do venv."
        }
        Write-Host "[.venv] Ambiente virtual criado com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "`n[Erro Crítico] Falha ao criar o ambiente virtual: $_" -ForegroundColor Red
        Read-Host "Pressione Enter para fechar..."
        exit 1
    }

    # Atualizar o pip no ambiente virtual recém-criado
    Write-Host "[pip] Atualizando o pip dentro do .venv..." -ForegroundColor Cyan
    try {
        & $venvPython -m pip install --upgrade pip --quiet
        Write-Host "[pip] Pip atualizado com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "[Aviso] Não foi possível atualizar o pip agora (o servidor continuará normalmente): $_" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "[Python] Ambiente virtual detectado: .venv" -ForegroundColor Green
}

$pythonExe = $venvPython

# -----------------------------------------------------------------------------
# 2. Varredura de Portas Disponíveis (Inicia em 8000)
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

$porta = $PortaInicial
while ($porta -lt ($PortaInicial + 100)) {
    if (-not (Test-PortInUse $porta)) {
        break
    }
    Write-Host "[Porta] A porta $porta já está em uso. Verificando porta $( $porta + 1 )..." -ForegroundColor DarkYellow
    $porta++
}

$url = "http://localhost:$porta"
Write-Host "[Servidor] Porta disponível selecionada: $porta" -ForegroundColor Green
Write-Host "[Servidor] Abrindo nova janela de terminal para executar o servidor..." -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 3. Executar o Servidor em Novo Terminal e Abrir Navegador
# -----------------------------------------------------------------------------
$scriptBlockText = @"
`$host.UI.RawUI.WindowTitle = 'Servidor - Provas de Vestibulares (Porta $porta)'
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '      Servidor Ativo - Provas de Vestibulares            ' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host 'URL Local: $url' -ForegroundColor Green
Write-Host 'Pressione Ctrl+C para encerrar o servidor local.`n' -ForegroundColor Gray
try {
    & '$pythonExe' '$scriptDir\server.py' $porta
} catch {
    Write-Host "`n[Erro no Servidor] `$_" -ForegroundColor Red
} finally {
    Write-Host "`n[Servidor encerrado]" -ForegroundColor Yellow
    Read-Host 'Pressione Enter para fechar esta janela...'
}
"@

$bytes = [System.Text.Encoding]::Unicode.GetBytes($scriptBlockText)
$encodedCommand = [Convert]::ToBase64String($bytes)

$processInfo = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedCommand `
    -PassThru

# Aguarda o servidor iniciar e estar escutando na porta antes de abrir o navegador
$tentativas = 0
while ($tentativas -lt 25 -and -not (Test-PortInUse $porta)) {
    Start-Sleep -Milliseconds 150
    $tentativas++
}

Write-Host "[Navegador] Abrindo $url no navegador..." -ForegroundColor Cyan
Start-Process $url

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Servidor em execução com sucesso na nova janela!        " -ForegroundColor Green
Write-Host "  PID do processo: $($processInfo.Id)" -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Para acompanhar os logs ou encerrar o servidor, utilize a nova janela aberta.`n" -ForegroundColor Gray


