# ============================================================
# VW Scraper - Windows Task Scheduler Kurulumu
# PowerShell'i YONETICI modunda calistirin:
#   Right-click PowerShell -> "Run as Administrator"
#   .\setup_task_scheduler.ps1
# ============================================================

$ScriptDir  = "C:\Users\T62443\vw_scraper"
$BatchFile  = Join-Path $ScriptDir "run_scraper.bat"
$TaskName   = "VW_Fiyat_Scraper"
$TriggerTime = "09:00"  # Her gun saat 09:00

Write-Host ""
Write-Host "VW Scraper - Task Scheduler Kurulumu" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Eski gorevi varsa sil
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[INFO] Eski gorev silindi." -ForegroundColor Yellow
}

# Trigger: Her gun belirtilen saatte
$trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# Action: batch dosyasini calistir
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchFile`"" `
    -WorkingDirectory $ScriptDir

# Ayarlar
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Gorevi kaydet
Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "[OK] Gorev olusturuldu: '$TaskName'" -ForegroundColor Green
Write-Host "[OK] Her gun saat $TriggerTime de otomatik calisacak." -ForegroundColor Green
Write-Host ""

# Gorev bilgisi goster
$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "Gorev detaylari:"
Write-Host "  Durum : $($task.State)"
Write-Host "  Path  : $BatchFile"
Write-Host ""
Write-Host "Iptal etmek icin:" -ForegroundColor DarkGray
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Manuel calistirmak icin:" -ForegroundColor DarkGray
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor DarkGray
