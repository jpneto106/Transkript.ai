@echo off
REM Abre a versao 4 (em desenvolvimento) sem precisar instalar nem publicar.
REM Se a casca ainda nao foi compilada em Debug, compila agora (dotnet build).
REM Antes de abrir a janela, confere se os componentes publicaveis (servidor,
REM frontend, ffmpeg) ja estao presentes; se faltar alguma coisa, usa o
REM buscador do instalador bootstrap para baixar do GitHub Releases.
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

REM Confere e baixa componentes publicaveis que porventura faltem.
echo Conferindo componentes (servidor, frontend, ffmpeg)...
venv\Scripts\python.exe instalador\baixar_componentes.py --skip cuda,modelos-diarizacao --destino . 2>nul
if errorlevel 1 (
    echo AVISO: o buscador de componentes falhou. A janela vai abrir mesmo assim,
    echo         mas o servidor/frontend poderao nao estar presentes.
)

start "" "%EXE%"
