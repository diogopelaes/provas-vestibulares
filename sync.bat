@echo off
:: ===============================================================================
:: ARQUIVO: sync.bat
:: CAMADA: Automação / Launcher Batch para Windows
:: PAPEL NO SISTEMA:
::   - Ponto de entrada rápido com duplo-clique no Windows Explorer.
::   - Executa o script PowerShell sync.ps1 com bypass de política de execução.
::   - Repassa parâmetros opcionais (ex: "mensagem do commit").
::   - Garante que a janela permaneça aberta em caso de erro para diagnóstico.
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] A sincronização terminou com código de saída: %ERRORLEVEL%
    echo.
    pause
)
