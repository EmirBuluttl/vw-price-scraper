@echo off
chcp 65001 >nul
echo ============================================================
echo  CAR PRICE SCRAPER WEB DASHBOARD SUNUCUSU
echo ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "SYS_PY=python"

if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
) else (
    set "PY=%SYS_PY%"
)

echo Python: %PY%
echo Web Arayüzü Başlatılıyor...
echo Tarayıcınızda açın: http://localhost:5000
echo.

:: Tarayıcıyı 2 saniye sonra otomatik aç
start "" "http://localhost:5000"

:: Flask Sunucusunu Başlat
"%PY%" "%SCRIPT_DIR%app.py"

pause
