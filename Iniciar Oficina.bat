@echo off
setlocal
cd /d "%~dp0"
title Oficina Manager

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>&1
    if errorlevel 1 (
        echo Python nao encontrado.
        pause
        exit /b 1
    )
    py -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt

start "" /min cmd /c ""%~dp0.venv\Scripts\python.exe" "%~dp0app.py" > "%~dp0servidor.log" 2>&1"

for /l %%i in (1,1,20) do (
    powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000 -TimeoutSec 1).StatusCode; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto OPEN
    timeout /t 1 /nobreak >nul
)
echo O servidor nao respondeu.
echo Verifica servidor.log e erro.log.
pause
exit /b 1
:OPEN
start "" "http://localhost:5000"
exit
