<#
===============================================================================
ARQUIVO: dev/sync_server.ps1
CAMADA: Automação / Pipeline de Sincronização e Versionamento
PAPEL NO SISTEMA:
  1. Localiza o ambiente virtual (.venv) ou o Python configurado.
  2. Executa dev/sync_server.py para sincronizar incrementalmente os arquivos
     da pasta media/ e o banco de dados local com o servidor de produção.
  3. Caso haja alterações (novos PDFs baixados, registros, etc.), executa
     automaticamente 'git add -A', 'git commit' e 'git push'.
===============================================================================
#>

[CmdletBinding()]
param (
    [string]$Mensagem = "Sincronização do acervo com servidor de produção ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))",
    [switch]$ForcePush
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# 1. Resolução de Caminhos e Ambiente
# -----------------------------------------------------------------------------
$rootDir = if (Test-Path (Join-Path $PSScriptRoot "manage.py")) {
    $PSScriptRoot
} else {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

Set-Location $rootDir

# Resolução de Python conforme regras do ambiente
$venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
$fallbackPython = "C:\Users\Diogo\AppData\Local\Python\pythoncore-3.14-64\python.exe"

$pythonExe = if (Test-Path $venvPython) {
    $venvPython
} elseif (Test-Path $fallbackPython) {
    $fallbackPython
} else {
    (Get-Command python.exe -ErrorAction Stop).Source
}

$syncScript = Join-Path $rootDir "dev\sync_server.py"
if (-not (Test-Path $syncScript)) {
    Write-Host "[ERRO] Script de sincronização não encontrado: $syncScript" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------------
# 2. Executar Sincronização Inteligente (dev/sync_server.py)
# -----------------------------------------------------------------------------
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Iniciando Pipeline de Sincronização com o Servidor    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Diretório do projeto : $rootDir" -ForegroundColor Gray
Write-Host "Executável Python     : $pythonExe" -ForegroundColor Gray
Write-Host "Script de sincronismo: $syncScript`n" -ForegroundColor Gray

& $pythonExe $syncScript @args
$syncExitCode = $LASTEXITCODE

if ($syncExitCode -ne 0) {
    Write-Host "`n[ERRO CRÍTICO] Falha na execução do sync_server.py (código: $syncExitCode). Abortando git commit e push." -ForegroundColor Red
    exit $syncExitCode
}

# -----------------------------------------------------------------------------
# 3. Verificar Alterações no Git
# -----------------------------------------------------------------------------
Write-Host "`n[Git] Verificando status do repositório local..." -ForegroundColor Cyan

$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    # Verifica se há commits locais ainda não enviados
    $branchStatus = git status -sb
    if ($branchStatus -match "ahead\s+(\d+)") {
        $pendentes = $Matches[1]
        Write-Host "[Git] Existem $pendentes commit(s) locais pendentes de envio. Executando git push..." -ForegroundColor Yellow
        git push
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n[Sucesso] Commits pendentes enviados com sucesso!`n" -ForegroundColor Green
        }
    } else {
        Write-Host "[Git] Nenhuma alteração pendente de commit ou push. O repositório já está atualizado.`n" -ForegroundColor Green
    }
    exit 0
}

Write-Host "[Git] Arquivos modificados/adicionados detectados:" -ForegroundColor Yellow
$status | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

# -----------------------------------------------------------------------------
# 4. Git Add, Commit e Push
# -----------------------------------------------------------------------------
Write-Host "`n[Git] Adicionando arquivos alterados (git add -A)..." -ForegroundColor Cyan
git add -A

Write-Host "[Git] Criando commit com mensagem: '$Mensagem'..." -ForegroundColor Cyan
git commit -m $Mensagem
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao realizar git commit." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[Git] Enviando commits para o repositório remoto (git push)..." -ForegroundColor Cyan
if ($ForcePush) {
    git push --force
} else {
    git push
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao realizar git push." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Pipeline de Sincronização e Push Concluído com Sucesso! " -ForegroundColor Green
Write-Host "==========================================================`n" -ForegroundColor Green

