@echo off
chcp 65001 >nul
echo ============================================================
echo  COKLU MARKA ARAC FIYAT SCRAPER
echo  %date% %time%
echo ============================================================

:: Python'u bul — hem sistem hem de venv kontrol et
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "SYS_PY=python"

if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
) else (
    set "PY=%SYS_PY%"
)

echo Python: %PY%
echo.

:: Bağımlılıkları yükle (ilk çalıştırmada)
"%PY%" -m pip install -q -r "%SCRIPT_DIR%requirements.txt"

:: Tüm markaları çalıştır
"%PY%" "%SCRIPT_DIR%multi_scraper.py" %*

echo.
echo ============================================================
echo  Tamamlandi: %date% %time%
echo ============================================================

:: Task Scheduler'dan çalıştırıldığında pencereyi açık tut (isteğe bağlı)
:: pause
