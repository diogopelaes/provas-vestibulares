#!/usr/bin/env bash
# ==============================================================================
# Script de Deploy e Atualização Contínua - Provas de Vestibulares
# VPS: acervo.diogo.mat.br
#
# Execução:
#   chmod +x deploy.sh
#   ./deploy.sh
# ==============================================================================

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${APP_DIR}"

echo "=================================================================="
echo "  Deploy / Atualização: Acervo de Vestibulares (acervo.diogo.mat.br)  "
echo "  Diretório: ${APP_DIR}"
echo "=================================================================="

# ------------------------------------------------------------------------------
# 1. Sincronização Forçada com o Repositório Remoto
#    Garante que o repositório local fique estritamente idêntico ao remoto,
#    sem permitir que modificações locais subam ou conflitem.
#    Preserva: media/, .env, db.sqlite3, .search_cache.db e .venv/
# ------------------------------------------------------------------------------
echo ""
echo "[1/7] Sincronizando repositório Git com a branch remota..."

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
if [ "${CURRENT_BRANCH}" = "HEAD" ]; then
    CURRENT_BRANCH="main"
fi

git fetch origin "${CURRENT_BRANCH}"
git reset --hard "origin/${CURRENT_BRANCH}"

# Limpa artefatos não rastreados, preservando dados cruciais
git clean -fd \
    -e media \
    -e media/** \
    -e .env \
    -e db.sqlite3 \
    -e app/.search_cache.db \
    -e .venv

echo " -> Repositório alinhado com origin/${CURRENT_BRANCH} com sucesso."

# ------------------------------------------------------------------------------
# 2. Ambiente Virtual (.venv)
# ------------------------------------------------------------------------------
echo ""
echo "[2/7] Verificando ambiente virtual Python (.venv)..."
if [ ! -d ".venv" ]; then
    echo " -> Criando ambiente virtual..."
    if command -v python3.14 &>/dev/null; then
        python3.14 -m venv .venv
    elif command -v python3 &>/dev/null; then
        python3 -m venv .venv
    else
        echo "ERRO: python3 não encontrado no servidor."
        exit 1
    fi
fi

# Ativação do ambiente virtual
# shellcheck disable=SC1091
source .venv/bin/activate

echo " -> Atualizando pip e instalando dependências..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ------------------------------------------------------------------------------
# 3. Configuração de Variáveis de Ambiente (.env)
# ------------------------------------------------------------------------------
echo ""
echo "[3/7] Verificando arquivo .env..."
if [ ! -f ".env" ]; then
    echo " -> Gerando .env padrão para produção..."
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
    cat <<EOF > .env
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=acervo.diogo.mat.br,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://acervo.diogo.mat.br
EOF
    echo " -> Arquivo .env criado com SECRET_KEY segura."
fi

# ------------------------------------------------------------------------------
# 4. Migrações do Banco de Dados
# ------------------------------------------------------------------------------
echo ""
echo "[4/7] Aplicando migrações do banco de dados (Django)..."
python manage.py migrate --noinput

# ------------------------------------------------------------------------------
# 5. Coleta de Arquivos Estáticos (Collectstatic)
# ------------------------------------------------------------------------------
echo ""
echo "[5/7] Coletando arquivos estáticos para /staticfiles..."
python manage.py collectstatic --noinput

# ------------------------------------------------------------------------------
# 6. Sincronização do Índice de Busca dos PDFs
# ------------------------------------------------------------------------------
echo ""
echo "[6/7] Verificando integridade e indexando novos PDFs..."
mkdir -p media
python manage.py sync_search || echo "Aviso: Indexação em segundo plano ou pendente."

# ------------------------------------------------------------------------------
# 7. Permissões e Reinício dos Serviços
# ------------------------------------------------------------------------------
echo ""
echo "[7/7] Ajustando permissões e reiniciando serviços..."

# Garante permissões adequadas para o usuário do servidor web (ex: www-data)
if id "www-data" &>/dev/null; then
    chown -R www-data:www-data media staticfiles db.sqlite3 app/.search_cache.db 2>/dev/null || true
fi
chmod -R 775 media staticfiles 2>/dev/null || true
[ -f "db.sqlite3" ] && chmod 664 db.sqlite3 2>/dev/null || true
[ -f "app/.search_cache.db" ] && chmod 664 app/.search_cache.db 2>/dev/null || true

# Reinicia serviço Systemd da aplicação
if systemctl list-unit-files | grep -q "provas-vestibulares.service"; then
    echo " -> Reiniciando systemd service 'provas-vestibulares'..."
    sudo systemctl daemon-reload 2>/dev/null || true
    sudo systemctl restart provas-vestibulares
    sudo systemctl status provas-vestibulares --no-pager -l || true
else
    echo " -> Aviso: Unidade systemd 'provas-vestibulares.service' não instalada."
    echo "    Para instalar: sudo cp dev/provas-vestibulares.service /etc/systemd/system/"
    echo "                   sudo systemctl daemon-reload && sudo systemctl enable --now provas-vestibulares"
fi

# Recarrega o Caddy se estiver ativo
if systemctl is-active --quiet caddy 2>/dev/null; then
    echo " -> Recarregando configurações do Caddy..."
    sudo systemctl reload caddy 2>/dev/null || true
fi

echo ""
echo "=================================================================="
echo "  Deploy finalizado com sucesso!                                "
echo "  Acesse: https://acervo.diogo.mat.br                            "
echo "=================================================================="

