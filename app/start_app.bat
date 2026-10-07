@echo off
:: ===============================================================================
:: ARQUIVO: app/start_app.bat
:: CAMADA: Automação / Launcher Batch para Windows
:: PAPEL NO SISTEMA:
::   - Ponto de entrada rápido com duplo-clique no Windows Explorer.
::   - Executa de forma transparente o script PowerShell start_app.ps1
::     ignorando restrições de ExecutionPolicy temporariamente no processo.
::   - Garante que a janela permaneça aberta em qualquer cenário (erro ou encerramento).
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_app.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] O processo foi finalizado com código de saída: %ERRORLEVEL%
)

echo.
pause
