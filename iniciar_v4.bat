@echo off
REM Abre a versao 4 (em desenvolvimento) sem precisar instalar nem publicar.
REM Se a casca ainda nao foi compilada em Debug, compila agora (dotnet build).
REM A janela vai abrir pegando o servidor pelo venv/ da propria pasta.
cd /d "%~dp0"

set EXE=casca\bin\Debug\net10.0-windows\Transkript.ai.exe

if not exist "%EXE%" (
    echo Casca ainda nao compilada em Debug. Compilando agora...
    dotnet build casca -c Debug -v quiet --nologo
    if errorlevel 1 (
        echo.
        echo ERRO: a compilacao falhou. Rode "dotnet build casca -c Debug" para ver detalhes.
        pause
        exit /b 1
    )
)

start "" "%EXE%"
