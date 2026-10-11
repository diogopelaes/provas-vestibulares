@echo off
:: ===============================================================================
:: ARQUIVO: app/sync.bat
:: CAMADA: Automação / Atalho Batch para Windows
:: PAPEL NO SISTEMA:
::   - Permite acionar a sincronização diretamente a partir da pasta app/.
::   - Delega a execução para o script central sync.bat localizado na raiz do projeto.
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0.."

call "%~dp0..\sync.bat" %*
