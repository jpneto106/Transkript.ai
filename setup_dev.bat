@echo off
REM Prepara o ambiente de desenvolvimento para a versao 4.
REM Faz, em ordem:
REM   1. Cria venv\ se nao existir
REM   2. Instala requirements.txt + requirements-api.txt
REM   3. Faz npm install + npm run build no frontend (gera frontend\dist\)
REM   4. Compila a casca em Debug (dotnet build)
REM Ate pode ser rodado mais de uma vez (e idempotente).
cd /d "%~dp0"

setlocal

if not exist "venv\Scripts\python.exe" (
    echo Criando venv...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: nao consegui criar o venv. Verifique se o Python 3.11+ esta no PATH.
        pause
        exit /b 1
    )
)

echo Instalando dependencias Python...
venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.txt -r requirements-api.txt
if errorlevel 1 (
    echo AVISO: pip install retornou erro. Pode ser instabilidade de rede — rode de novo.
)

if not exist "frontend\package.json" (
    echo ERRO: nao achei frontend\package.json. A interface web esta faltando?
    pause
    exit /b 1
)

cd frontend
if not exist "node_modules" (
    echo Rodando npm install (demora na primeira vez)...
    call npm install
    if errorlevel 1 (
        echo ERRO: npm install falhou. Verifique se o Node.js 18+ esta no PATH.
        pause
        cd ..
        exit /b 1
    )
)
echo Compilando a interface (npm run build)...
call npm run build
if errorlevel 1 (
    echo ERRO: npm run build falhou.
    pause
    cd ..
    exit /b 1
)
cd ..

echo Compilando a casca em Debug...
dotnet build casca -c Debug -v quiet --nologo
if errorlevel 1 (
    echo ERRO: dotnet build casca -c Debug falhou.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo   Pronto. Para abrir o programa, clique iniciar_v4.bat
echo =======================================================
pause
