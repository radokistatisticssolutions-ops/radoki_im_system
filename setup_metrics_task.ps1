# PowerShell Script to Create Windows Task Scheduler Job
# Run this script as Administrator

# Define variables
$TaskName = "RADOKI Collect System Metrics"
$BatchFile = "C:\Users\HP\Documents\Training\radoki_im_system\collect_metrics.bat"
$Description = "Automatically collect system metrics for RADOKI IMS"

# Create task action
$Action = New-ScheduledTaskAction -Execute $BatchFile

# Create task trigger (every 5 minutes)
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -At (Get-Date) -Once

# Create task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

# Register the task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description $Description -Force

Write-Host "Task created successfully"
Write-Host "Task: $TaskName"
Write-Host "Schedule: Every 5 minutes"
