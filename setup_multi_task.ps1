# setup_multi_task.ps1  —  Çoklu Marka Scraper için Windows Task Scheduler Kurulumu
# ===================================================================================
# Yönetici olarak çalıştırın:
#   Right-click > "Run as Administrator"
# veya PowerShell'de:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\setup_multi_task.ps1

$ErrorActionPreference = "Stop"

# ─── Ayarlar ───────────────────────────────────────────────────────────────────
$TaskName    = "MultiCarPriceScraper"
$TaskDesc    = "Renault, Ford, VW, Hyundai, Toyota, Chery fiyat scraper — Her sabah 09:00"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile   = Join-Path $ScriptDir "run_multi_scraper.bat"
$LogFile     = Join-Path $ScriptDir "multi_scraper.log"
$TriggerTime = "09:00"

# ─── Mevcut görevi kaldır (varsa) ──────────────────────────────────────────────
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Mevcut gorev kaldiriliyor: $TaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# ─── Yeni görevi oluştur ───────────────────────────────────────────────────────
$Action  = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchFile`" >> `"$LogFile`" 2>&1" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $TriggerTime

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal `
    -Description $TaskDesc `
    -Force

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Gorev olusturuldu: $TaskName" -ForegroundColor Green
Write-Host "  Tetikleyici: Her gun saat $TriggerTime" -ForegroundColor Green
Write-Host "  Script: $BatchFile" -ForegroundColor Green
Write-Host "  Log: $LogFile" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ─── Hemen test calistir ───────────────────────────────────────────────────────
$TestNow = Read-Host "Gorevi simdi test etmek ister misiniz? (E/H)"
if ($TestNow -eq "E" -or $TestNow -eq "e" -or $TestNow -eq "Y" -or $TestNow -eq "y") {
    Write-Host "Gorev baslatiliyor..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Gorev baslatildi. Log: $LogFile" -ForegroundColor Green
}
