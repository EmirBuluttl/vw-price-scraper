@echo off
REM ============================================================
REM  VW Fiyat Scraper - Gunluk otomatik calistirma
REM  Bu dosya Windows Task Scheduler tarafindan calistirilir
REM ============================================================
set SCRIPT_DIR=%~dp0
set PYTHON=python

echo [%date% %time%] VW Scraper baslatildi >> "%SCRIPT_DIR%runner.log"

cd /d "%SCRIPT_DIR%"
%PYTHON% -X utf8 scraper.py >> "%SCRIPT_DIR%runner.log" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Basarili tamamlandi >> "%SCRIPT_DIR%runner.log"
) else (
    echo [%date% %time%] HATA! Exit code: %ERRORLEVEL% >> "%SCRIPT_DIR%runner.log"
)
