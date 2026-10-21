# Source-qualified F139 Windows startup harness. Safe by default: no mutation.
[CmdletBinding()]
param(
  [string]$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source,
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'FORGE-F139'),
  [string]$TaskName = 'FORGE-F139-UnifiedController',
  [switch]$Apply,
  [switch]$Remove,
  [switch]$ConfigureKey
)
$ErrorActionPreference = 'Stop'
if ($Apply -and $Remove) { throw 'F139_CONFLICTING_TASK_ACTIONS' }
# PS 5.1 has no $IsWindows; .NET platform identity works on Desktop and Core.
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
  if ($Apply -or $Remove -or $ConfigureKey) { throw 'F139_WINDOWS_ONLY_MUTATION' }
}
if ($TaskName -ne 'FORGE-F139-UnifiedController') { throw 'F139_TASK_NAME_NOT_QUALIFIED' }
if (!(Test-Path -LiteralPath (Join-Path $RepositoryRoot 'f139/local_controller.py'))) {
  throw 'F139_SOURCE_ABSENT'
}
if (-not $PythonExe -or !(Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
  throw 'F139_PYTHON_RUNTIME_MISSING'
}
$runner = Join-Path $PSScriptRoot 'Run-FORGE-F139.ps1'
if (!(Test-Path -LiteralPath $runner -PathType Leaf)) { throw 'F139_RUNNER_MISSING' }
$jobSource = Join-Path $PSScriptRoot 'F139WindowsJobSupervisor.cs'
if (!(Test-Path -LiteralPath $jobSource -PathType Leaf)) { throw 'F139_WINDOWS_JOB_SOURCE_MISSING' }
$db = Join-Path $StateDirectory 'state.sqlite'
$key = Join-Path $StateDirectory 'worker-hmac.dpapi.xml'
$ps = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
if (-not $ps -and $Apply) { throw 'F139_WINDOWS_POWERSHELL_MISSING' }
Write-Host "F139_SOURCE=$RepositoryRoot"
Write-Host "F139_DATABASE=$db"
Write-Host "F139_TASK=$TaskName"
Write-Host 'F139_DOES_NOT_DISABLE_LEGACY=TRUE'
Write-Host 'F139_CLOUDFLARE_CONTROLLER=FALSE'
# The controller host may be on battery: never let Task Scheduler strand it queued.
# Construct and verify the very settings object that -Apply registers.
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  if ($settings.DisallowStartIfOnBatteries -or $settings.StopIfGoingOnBatteries) {
    throw 'F139_BATTERY_POLICY_NOT_ADMISSIBLE'
  }
  Write-Host 'F139_BATTERY_ADMISSION_CONFIG=PASS'
}
if (-not ($Apply -or $Remove -or $ConfigureKey)) {
  Write-Host 'F139_INSTALL=DRY_RUN_NO_CHANGES'
  return
}
if ($ConfigureKey) {
  New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
  if (Test-Path -LiteralPath $key) { throw 'F139_EXISTING_DPAPI_KEY_NOT_OVERWRITTEN' }
  $secure = Read-Host 'Enter the same high-entropy key configured as the GitHub F139_WORKER_HMAC_KEY secret' -AsSecureString
  $secure | Export-Clixml -LiteralPath $key
  Write-Host 'F139_DPAPI_SECRET=CONFIGURED_CURRENT_WINDOWS_USER_ONLY'
}
if ($Remove) {
  $found = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($found) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }
  Write-Host 'F139_TASK_REMOVED_DATABASE_AND_EVIDENCE_PRESERVED'
  return
}
if ($Apply) {
  if (!(Test-Path -LiteralPath $db -PathType Leaf)) { throw 'F139_DATABASE_NOT_INITIALIZED' }
  $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
  $arg = @('-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass',
    '-File',('"'+$runner+'"'),'-PythonExe',('"'+$PythonExe+'"'),
    '-RepositoryRoot',('"'+$RepositoryRoot+'"'),'-Database',('"'+$db+'"'),
    '-EncryptedKeyFile',('"'+$key+'"')) -join ' '
  $action = New-ScheduledTaskAction -Execute $ps -Argument $arg
  # Reuse ONE original task; ignore overlapping starts while its job
  # supervisor owns the long-running Python process. Re-wake after unexpected
  # stop or console-control termination without a second scheduler/controller.
  $owner = ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
  $logon = New-ScheduledTaskTrigger -AtLogOn -User $owner
  $shortWake = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Days 365)
  # The daily long-lived fallback survives expiry of the bounded 365-day
  # short wake; source-qualified reinstall can renew the 10-minute horizon.
  $dailyWake = New-ScheduledTaskTrigger -Daily -At '00:05'
  $trigger = @($logon, $shortWake, $dailyWake)
  if (@($trigger).Count -ne 3 -or $null -eq $shortWake.Repetition `
      -or $shortWake.Repetition.Interval -ne 'PT10M') {
    throw 'F139_SINGLE_TASK_WAKE_TRIGGERS_UNQUALIFIED'
  }
  Write-Host 'F139_EXISTING_TASK_WAKE_10MIN_AND_DAILY=PASS'
  if ($null -eq $settings) { throw 'F139_TASK_SETTINGS_ABSENT' }
  $task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings
  Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
  Write-Host 'F139_TASK_INSTALLED_INERT_UNTIL_SEPARATE_VERIFIED_CUTOVER'
}
