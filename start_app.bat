@echo off
:: ===============================================================================
:: ARQUIVO: start_app.bat
:: CAMADA: Automação / Launcher Batch para Windows
:: PAPEL NO SISTEMA:
::   - Ponto de entrada rápido com duplo-clique no Windows Explorer na raiz.
::   - Executa o start_app.ps1 de forma transparente.
::   - Fecha esta janela automaticamente após iniciar o servidor e abrir o navegador.
::   - Pausa apenas em caso de erro para diagnóstico.
:: ===============================================================================

chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_app.ps1" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] O processo foi finalizado com código de saída: %ERRORLEVEL%
    echo.
    pause
)
