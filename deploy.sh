#!/usr/bin/env bash
# ==============================================================================
# Script de Atualização Contínua - Provas de Vestibulares
# VPS: acervo.diogo.mat.br | Diretório: /var/www/provas-vestibulares
#
# COMO EXECUTAR NA VPS PARA ATUALIZAR:
#   cd /var/www/provas-vestibulares && ./deploy.sh
# ==============================================================================

set -euo pipefail

TARGET_DIR="/var/www/provas-vestibulares"
if [ -d "${TARGET_DIR}" ]; then
    APP_DIR="${TARGET_DIR}"
else
    APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

cd "${APP_DIR}"

echo "=================================================================="
echo "  Atualizando Acervo de Vestibulares (acervo.diogo.mat.br)"
echo "  Diretório: ${APP_DIR}"
echo "=================================================================="

# ------------------------------------------------------------------------------
# 1. Sincronização Forçada com o Repositório Remoto
#    Garante que o repositório local fique estritamente idêntico ao GitHub.
#    Preserva dados locais: media/, .env, db.sqlite3, .search_cache.db e .venv/
# ------------------------------------------------------------------------------
echo ""
echo "[1/6] Sincronizando com a branch remota..."

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
if [ "${CURRENT_BRANCH}" = "HEAD" ]; then
    CURRENT_BRANCH="main"
fi

git fetch origin "${CURRENT_BRANCH}"
git reset --hard "origin/${CURRENT_BRANCH}"

# Limpa arquivos não rastreados, protegendo mídia, banco e ambiente
git clean -fd \
    -e media \
    -e media/** \
    -e .env \
    -e db.sqlite3 \
    -e app/.search_cache.db \
    -e .venv

echo " -> Repositório alinhado com origin/${CURRENT_BRANCH} com sucesso."

# ------------------------------------------------------------------------------
# 2. Ambiente Virtual (.venv) e Dependências
# ------------------------------------------------------------------------------
echo ""
echo "[2/6] Verificando ambiente virtual e dependências..."
if [ ! -d ".venv" ]; then
    echo "ERRO: Ambiente virtual .venv não encontrado. Execute primeiro_deploy.sh."
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt --quiet

# ------------------------------------------------------------------------------
# 3. Migrações do Banco de Dados
# ------------------------------------------------------------------------------
echo ""
echo "[3/6] Aplicando migrações pendentes do Django..."
python manage.py migrate --noinput

# ------------------------------------------------------------------------------
# 4. Coleta de Arquivos Estáticos
# ------------------------------------------------------------------------------
echo ""
echo "[4/6] Coletando arquivos estáticos atualizados..."
python manage.py collectstatic --noinput

# ------------------------------------------------------------------------------
# 5. Sincronização do Acervo de PDFs
# ------------------------------------------------------------------------------
echo ""
echo "[5/6] Verificando novos PDFs em media/ e atualizando índices..."
python manage.py sync_search || true
python manage.py cadastrar_provas_iniciais --username "diogo" || true

# Permissões adequadas para o usuário www-data
mkdir -p media staticfiles
if id "www-data" &>/dev/null; then
    sudo chown -R www-data:www-data media staticfiles 2>/dev/null || chown -R www-data:www-data media staticfiles 2>/dev/null || true
    [ -f "db.sqlite3" ] && (sudo chown www-data:www-data db.sqlite3 2>/dev/null || chown www-data:www-data db.sqlite3 2>/dev/null || true)
    [ -f "app/.search_cache.db" ] && (sudo chown www-data:www-data app/.search_cache.db 2>/dev/null || chown www-data:www-data app/.search_cache.db 2>/dev/null || true)
    [ -f ".env" ] && (sudo chown www-data:www-data .env 2>/dev/null || chown www-data:www-data .env 2>/dev/null || true)
    sudo chgrp www-data "${APP_DIR}" "${APP_DIR}/app" 2>/dev/null || true
    sudo chmod g+rwx "${APP_DIR}" "${APP_DIR}/app" 2>/dev/null || true
fi
chmod -R 775 media staticfiles 2>/dev/null || true
[ -f "db.sqlite3" ] && chmod 664 db.sqlite3 2>/dev/null || true
[ -f "app/.search_cache.db" ] && chmod 664 app/.search_cache.db 2>/dev/null || true
[ -f ".env" ] && chmod 644 .env 2>/dev/null || true

# ------------------------------------------------------------------------------
# 6. Reiniciar Serviços
# ------------------------------------------------------------------------------
echo ""
echo "[6/6] Reiniciando serviço 'provas-vestibulares' e recarregando Caddy..."
if [ -f "dev/provas-vestibulares.service" ]; then
    sudo cp dev/provas-vestibulares.service /etc/systemd/system/provas-vestibulares.service 2>/dev/null || cp dev/provas-vestibulares.service /etc/systemd/system/provas-vestibulares.service 2>/dev/null || true
    sudo systemctl daemon-reload 2>/dev/null || true
fi

sudo systemctl restart provas-vestibulares

if systemctl is-active --quiet caddy 2>/dev/null; then
    sudo systemctl reload caddy 2>/dev/null || systemctl reload caddy 2>/dev/null || true
fi

echo ""
echo " -> Status do serviço provas-vestibulares:"
sudo systemctl status provas-vestibulares --no-pager

echo ""
echo "=================================================================="
echo "  Aplicação atualizada com sucesso!"
echo "  URL: https://acervo.diogo.mat.br"
echo "=================================================================="
