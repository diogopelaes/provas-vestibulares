@echo off
:: ===============================================================================
:: ARQUIVO: app/sync.bat
:: CAMADA: Automacao / Atalho Batch para Windows
:: PAPEL NO SISTEMA:
::   - Permite acionar a sincronizacao diretamente a partir da pasta app/.
::   - Delega a execucao para o script central sync.bat localizado na raiz do projeto.
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0.."

call "%~dp0..\sync.bat" %*