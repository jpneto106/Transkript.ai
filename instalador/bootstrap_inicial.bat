@echo off
REM Baixador de componentes para o instalador bootstrap do Transkript.ai.
REM Espelho Windows do `baixar_componentes.py`. Roda em qualquer Windows 10/11
REM sem precisar de Python: usa PowerShell 5.1 (que ja vem no sistema) para
REM baixar do GitHub Releases, conferir o sha256 e extrair no lugar.
REM
REM Uso:
REM   bootstrap_inicial.bat [tag]
REM
REM Sem argumentos usa a tag padrao v4.0.0. Os argumentos extras vao para o
REM PowerShell (ex.: -DryRun, -Force, -Componentes servidor,ffmpeg).
cd /d "%~dp0"

set TAG=%1
if "%TAG%"=="" set TAG=v4.0.0

if "%2"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_inicial.ps1" -Tag "%TAG%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_inicial.ps1" -Tag "%TAG%" %2 %3 %4 %5 %6 %7 %8 %9
)

if errorlevel 1 (
    echo.
    echo ERRO: o bootstrap nao completou. Veja as mensagens acima.
    pause
    exit /b 1
)
