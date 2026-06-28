# register-scheduled-task.ps1
# Registers the nightly discharge update as a Windows Task Scheduler task.
# Run once from an elevated (Administrator) PowerShell session.

$scriptPath = Resolve-Path (Join-Path $PSScriptRoot 'nightly-discharge-update.ps1')
$taskName   = 'HITH – Nightly Discharge Update'
$taskDesc   = 'Promotes newly discharged HITH patients from dbo.referrals_flattened into hist.Activity_Fact_Referral on localhost\SQLDEVSERVER'

$action  = New-ScheduledTaskAction `
    -Execute   'pwsh.exe' `
    -Argument  "-NonInteractive -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At '02:00AM'

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit  (New-TimeSpan -Minutes 30) `
    -RestartCount        2 `
    -RestartInterval     (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -MultipleInstances   IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId    "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel  Highest

# Remove existing task if present, then register fresh
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName   $taskName `
    -Description $taskDesc `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal

Write-Host "Scheduled task '$taskName' registered - runs daily at 02:00."
