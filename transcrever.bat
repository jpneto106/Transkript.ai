@echo off
cd /d "%~dp0"
venv\Scripts\python.exe transcrever.py %*
echo.
pause
