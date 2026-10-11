<#
===============================================================================
ARQUIVO: sync.ps1
CAMADA: Automação / Sincronização Git (PowerShell)
PAPEL NO SISTEMA:
  - Realiza a sincronização 100% automática da aplicação e acervo com o GitHub:
      1. Valida o ambiente, presença do Git e integridade do repositório.
      2. Detecta a branch ativa e o repositório remoto (origin).
      3. Identifica alterações locais (arquivos modificados, novos ou removidos).
      4. Comita automaticamente alterações pendentes com timestamp (sem interação).
      5. Busca atualizações do remoto (git fetch).
      6. Integra novidades do remoto de forma limpa (git pull --rebase).
      7. Se houver commits locais, envia para o remoto (git push).
         * Tratamento inteligente para repositório público: se o usuário clonou
           o repositório e não tem permissão de escrita (apenas leitura),
           o script mantém as atualizações locais integradas via pull sem falhar!
      8. Executa sem pausas por padrão (dois cliques, roda e fecha).
===============================================================================
#>

[CmdletBinding()]
param (
    [Parameter()]
    [string]$Remote = "origin",

    [Parameter()]
    [switch]$Pausar
)

# Configuração de codificação para evitar problemas com acentuação e caracteres especiais
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$repoRoot = $PSScriptRoot
Set-Location -Path $repoRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      Sincronização - Central de Provas Vestibulares     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Diretório de trabalho: $repoRoot`n" -ForegroundColor DarkGray

# -----------------------------------------------------------------------------
# 1. Verificações de Pré-requisitos
# -----------------------------------------------------------------------------
Write-Host "[1/5] Verificando ambiente e ferramentas..." -ForegroundColor Yellow

$gitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Host "[ERRO] O executável git.exe não foi encontrado no PATH do sistema." -ForegroundColor Red
    Write-Host "Por favor, instale o Git para Windows ou verifique suas variáveis de ambiente." -ForegroundColor Yellow
    Read-Host "Pressione Enter para fechar..."
    exit 1
}

# Verifica se o diretório atual é um repositório Git válido
$isInsideWorkTree = & git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0 -or $isInsideWorkTree -ne "true") {
    Write-Host "[ERRO] O diretório atual não é um repositório Git válido: $repoRoot" -ForegroundColor Red
    Read-Host "Pressione Enter para fechar..."
    exit 1
}

# Obtém a branch atual
$currentBranch = (& git branch --show-current 2>$null).Trim()
if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    $currentBranch = (& git rev-parse --abbrev-ref HEAD 2>$null).Trim()
}

if ([string]::IsNullOrWhiteSpace($currentBranch) -or $currentBranch -eq "HEAD") {
    Write-Host "[ERRO] Não foi possível determinar a branch ativa (possível detached HEAD)." -ForegroundColor Red
    Write-Host "Verifique o estado do repositório com 'git status' antes de sincronizar." -ForegroundColor Yellow
    Read-Host "Pressione Enter para fechar..."
    exit 1
}

# Verifica se o remote existe
$remoteUrl = (& git remote get-url $Remote 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remoteUrl)) {
    Write-Host "[ERRO] O remote '$Remote' não foi configurado neste repositório." -ForegroundColor Red
    Write-Host "Configure o remote com 'git remote add $Remote <URL>' antes de sincronizar." -ForegroundColor Yellow
    Read-Host "Pressione Enter para fechar..."
    exit 1
}

Write-Host " -> Git detectado: $(& git --version)" -ForegroundColor Green
Write-Host " -> Branch atual: $currentBranch" -ForegroundColor Green
Write-Host " -> Remote: $Remote ($remoteUrl)" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 2. Identificação e Registro de Alterações Locais (100% Automático)
# -----------------------------------------------------------------------------
Write-Host "`n[2/5] Verificando alterações locais..." -ForegroundColor Yellow

$statusLines = & git status --porcelain
if ($statusLines) {
    $quantidadeAlteracoes = @($statusLines).Count
    Write-Host " -> Detectadas $quantidadeAlteracoes alteração(ões) pendente(s) localmente:" -ForegroundColor Cyan
    
    foreach ($line in $statusLines) {
        Write-Host "    $line" -ForegroundColor Gray
    }

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $mensagemCommit = "sync: sincronização automática do acervo ($timestamp)"

    Write-Host "`n -> Adicionando arquivos modificados/novos (git add -A)..." -ForegroundColor DarkCyan
    & git add -A
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Falha ao adicionar arquivos ao stage do Git." -ForegroundColor Red
        Read-Host "Pressione Enter para fechar..."
        exit 1
    }

    Write-Host " -> Criando commit automático: '$mensagemCommit'..." -ForegroundColor DarkCyan
    & git commit -m "$mensagemCommit"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Falha ao realizar commit das alterações locais." -ForegroundColor Red
        Read-Host "Pressione Enter para fechar..."
        exit 1
    }

    Write-Host " -> Alterações commitadas com sucesso." -ForegroundColor Green
} else {
    Write-Host " -> Nenhuma alteração local pendente de commit." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------------
# 3. Busca de Atualizações Remotas (Fetch)
# -----------------------------------------------------------------------------
Write-Host "`n[3/5] Consultando repositório remoto ($Remote)..." -ForegroundColor Yellow

& git fetch $Remote 2>&1 | ForEach-Object {
    if (-not [string]::IsNullOrWhiteSpace($_)) {
        Write-Host "    $_" -ForegroundColor DarkGray
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERRO] Falha ao conectar ao repositório remoto '$Remote'." -ForegroundColor Red
    Write-Host "Verifique sua conexão com a internet." -ForegroundColor Yellow
    Read-Host "Pressione Enter para fechar..."
    exit 1
}

# -----------------------------------------------------------------------------
# 4. Integração de Alterações Remotas (Pull --rebase)
# -----------------------------------------------------------------------------
Write-Host "`n[4/5] Integrando alterações remotas..." -ForegroundColor Yellow

$remoteBranchRef = "$Remote/$currentBranch"
$hasRemoteBranch = $null
& git rev-parse --verify $remoteBranchRef 2>$null
if ($LASTEXITCODE -eq 0) {
    $hasRemoteBranch = $true
} else {
    $hasRemoteBranch = $false
}

if ($hasRemoteBranch) {
    $commitsAtrasRaw = (& git rev-list --count "HEAD..$remoteBranchRef" 2>$null)
    $commitsAtras = if ($commitsAtrasRaw) { [int]$commitsAtrasRaw.Trim() } else { 0 }

    if ($commitsAtras -gt 0) {
        Write-Host " -> Existem $commitsAtras commit(s) novo(s) no remoto. Aplicando (git pull --rebase)..." -ForegroundColor Cyan
        & git pull --rebase $Remote $currentBranch
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "`n==========================================================" -ForegroundColor Red
            Write-Host " [CONFLITO] Ocorreu um conflito ao mesclar as alterações!" -ForegroundColor Red
            Write-Host "==========================================================" -ForegroundColor Red
            Write-Host "Instruções para resolução:" -ForegroundColor Yellow
            Write-Host " 1. Abra os arquivos em conflito e resolva as diferenças." -ForegroundColor Gray
            Write-Host " 2. Execute 'git add <arquivos-resolvidos>'." -ForegroundColor Gray
            Write-Host " 3. Conclua com 'git rebase --continue'." -ForegroundColor Gray
            Write-Host " (Ou cancele o processo com 'git rebase --abort')" -ForegroundColor DarkYellow
            Read-Host "Pressione Enter para fechar..."
            exit 1
        }
        Write-Host " -> Atualizações remotas integradas com sucesso." -ForegroundColor Green
    } else {
        Write-Host " -> O repositório local já contém todos os commits remotos." -ForegroundColor DarkGray
    }
} else {
    Write-Host " -> A branch '$currentBranch' ainda não existe no remoto '$Remote'." -ForegroundColor Cyan
}

# -----------------------------------------------------------------------------
# 5. Envio de Alterações Locais (Push com Detecção de Permissão de Clone Público)
# -----------------------------------------------------------------------------
Write-Host "`n[5/5] Verificando envio para o repositório remoto (git push)..." -ForegroundColor Yellow

$commitsAfrente = 0
if ($hasRemoteBranch) {
    $commitsAfrenteRaw = (& git rev-list --count "$remoteBranchRef..HEAD" 2>$null)
    $commitsAfrente = if ($commitsAfrenteRaw) { [int]$commitsAfrenteRaw.Trim() } else { 0 }
} else {
    $commitsAfrente = 1
}

if ($commitsAfrente -gt 0) {
    Write-Host " -> Detectados $commitsAfrente commit(s) local(is) para envio." -ForegroundColor Cyan

    # Tenta o push capturando a saída
    $pushOutput = if (-not $hasRemoteBranch) {
        & git push -u $Remote $currentBranch 2>&1
    } else {
        & git push $Remote $currentBranch 2>&1
    }
    $pushExitCode = $LASTEXITCODE

    if ($pushExitCode -ne 0) {
        $pushOutputStr = ($pushOutput | Out-String)
        # Verifica se o erro foi decorrente de falta de permissão de escrita / autenticação (típico de clone público)
        $isPermissionError = (
            $pushOutputStr -match "Permission.*denied" -or
            $pushOutputStr -match "403" -or
            $pushOutputStr -match "Authentication failed" -or
            $pushOutputStr -match "could not read Username" -or
            $pushOutputStr -match "Invalid username or token"
        )

        if ($isPermissionError) {
            Write-Host " -> [AVISO INFORMATIVO] Repositório em modo somente leitura (clone público sem permissão de escrita no GitHub)." -ForegroundColor Yellow
            Write-Host " -> Todas as atualizações do repositório remoto foram baixadas e sincronizadas com seu acervo local com sucesso!" -ForegroundColor Green
        } else {
            Write-Host "`n[ERRO] Falha ao enviar alterações para o repositório remoto:" -ForegroundColor Red
            Write-Host $pushOutputStr -ForegroundColor DarkRed
            Read-Host "Pressione Enter para fechar..."
            exit 1
        }
    } else {
        Write-Host " -> Alterações enviadas com sucesso para '$Remote/$currentBranch'!" -ForegroundColor Green
    }
} else {
    Write-Host " -> Nada a enviar. O repositório remoto já está perfeitamente em dia." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------------
# Resumo Final
# -----------------------------------------------------------------------------
Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "      Sincronização Concluída com Sucesso!              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Status da branch '$currentBranch': Sincronizada." -ForegroundColor White

# Por padrão NÃO pausa (fecha direto). Pausa apenas se explicitamente solicitado com -Pausar.
if ($Pausar) {
    Write-Host ""
    Read-Host "Pressione Enter para fechar..."
}
