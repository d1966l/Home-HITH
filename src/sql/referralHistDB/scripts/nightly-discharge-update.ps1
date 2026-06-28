# nightly-discharge-update.ps1
# Executes usp_NightlyDischargeUpdate on localhost\SQLDEVSERVER
# Intended to be run by Windows Task Scheduler nightly at 02:00

$server   = 'localhost\SQLDEVSERVER'
$database = 'referralHistDB'
$logFile  = Join-Path $PSScriptRoot '..\logs\nightly-discharge-update.log'

$logDir = Split-Path $logFile -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

try {
    $result = Invoke-Sqlcmd `
        -ServerInstance $server `
        -Database $database `
        -Query 'EXEC dbo.usp_NightlyDischargeUpdate' `
        -ConnectionTimeout 30 `
        -QueryTimeout 120 `
        -ErrorAction Stop `
        -Verbose 4>&1

    $msg = "$timestamp | SUCCESS | $result"
    Write-Output $msg
    Add-Content -Path $logFile -Value $msg
}
catch {
    $errMsg = "$timestamp | ERROR | $($_.Exception.Message)"
    Write-Error $errMsg
    Add-Content -Path $logFile -Value $errMsg
    exit 1
}
