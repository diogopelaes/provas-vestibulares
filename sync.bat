@echo off
:: ===============================================================================
:: ARQUIVO: sync.bat
:: CAMADA: Automacao / Launcher Batch para Windows
:: PAPEL NO SISTEMA:
::   - Ponto de entrada rapido com duplo-clique no Windows Explorer.
::   - Executa o script PowerShell sync.ps1 com bypass de politica de execucao.
::   - Repassa parametros opcionais (ex: "mensagem do commit").
::   - Garante que a janela permanecera aberta em caso de erro para diagnostico.
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] A sincronizacao terminou com codigo de saida: %ERRORLEVEL%
    echo.
    pause
)