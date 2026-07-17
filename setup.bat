@echo off
REM ============================================================
REM  VW Scraper - Kurulum Scripti
REM  Tek seferlik çalıştırın
REM ============================================================
echo ╔══════════════════════════════════════════╗
echo ║   VW TR Fiyat Scraper - Kurulum          ║
echo ╚══════════════════════════════════════════╝
echo.

REM 1. Python kontrolü
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [HATA] Python bulunamadi! https://python.org adresinden indirin.
    pause
    exit /b 1
)
echo [OK] Python bulundu.

REM 2. pip ile playwright kur
echo.
echo [1/3] Playwright kuruluyor...
pip install playwright
if %ERRORLEVEL% NEQ 0 (
    echo [HATA] Playwright kurulamadi.
    pause
    exit /b 1
)

REM 3. Chromium browser indir
echo.
echo [2/3] Chromium browser indiriliyor (ilk seferinde ~150MB)...
playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo [HATA] Chromium indirilemedi.
    pause
    exit /b 1
)

echo.
echo [3/3] Test calistiriliyor...
python scraper.py

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Kurulum tamamlandi!                                     ║
echo ║                                                          ║
echo ║  Manuel calistirmak icin:                                ║
echo ║    python scraper.py                                     ║
echo ║                                                          ║
echo ║  Verileri gormek icin:                                   ║
echo ║    python view_data.py              (bugünün verisi)     ║
echo ║    python view_data.py --history    (fiyat gecmisi)     ║
echo ║    python view_data.py --logs       (calisma loglari)   ║
echo ║                                                          ║
echo ║  Otomatik icin: setup_task_scheduler.ps1 calistirin      ║
echo ╚══════════════════════════════════════════════════════════╝
pause
