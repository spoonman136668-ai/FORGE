# F139 V50: source-bound DEVELOPMENT-ONLY activation on the SAME original owner.
# Requires a distinct owner-authenticated issue #807 comment and exact
# protected-main eight-job regression. No scheduler, new controller or science.
param([Parameter(Mandatory=$true)][string]$Main,
      [Parameter(Mandatory=$true)][string]$Source)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$name='FORGE-F139-UnifiedController'
$originalDisabled=$false
$activationAttempted=$false
function Need([bool]$ok,[string]$why) {
  if(-not $ok){ throw ('F139_V50_NATIVE_'+$why) }
}
function Task {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try {
    $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
      Translate([Security.Principal.SecurityIdentifier]).Value
  } catch {}
  Need (@($t.Actions).Count -eq 1 -and @($t.Triggers).Count -eq 3 -and
    [IO.Path]::GetFileName([string]$t.Actions[0].Execute) -ieq 'powershell.exe' -and
    ([string]$t.Principal.UserId -ieq $who.Name -or
     $sid -ceq $who.User.Value)) 'ORIGINAL_TASK_IDENTITY_DRIFT'
  return $t
}
function Field($task,[string]$key) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success ('ORIGINAL_TASK_ARGUMENT_'+$key)
  return [string]$m.Groups[1].Value
}
function Children {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object { $_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database) })
}
function ExactSource {
  Need (Test-Path -LiteralPath $root -PathType Container) 'INSTALLED_ROOT_MISSING'
  $head=(& git -C $root rev-parse HEAD | Out-String).Trim()
  $dirty=@(& git -C $root status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $head -ceq $Source -and
    $dirty.Count -eq 0) 'INSTALLED_ORIGINAL_SOURCE_DRIFT'
}
function InvokeV50([string]$mode) {
  $env:PYTHONPATH=$env:GITHUB_WORKSPACE
  $lines=@(& $python -B -m f139.nci04_v50_original_native_activation --mode $mode --db $database)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
    $lines[0].StartsWith('F139_V50_OWNER_'+$mode.ToUpper()+'=',
       [StringComparison]::Ordinal)) ('PYTHON_'+$mode.ToUpper()+'_DENIED')
  return $lines[0].Split('=',2)[1]|ConvertFrom-Json
}
Need ($Main -cmatch '^[a-f0-9]{40}$' -and
  $Source -ceq '4ccbb84785a43e038453d6f2bda5415ecb364084' -and
  $env:GITHUB_SHA -ceq $Main -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'EXACT_ORIGINAL_OWNER_WORKFLOW_REQUIRED'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
$required='F139-V50-OWNER-NATIVE-ACTIVATE '+$Main+' '+$Source+' 43973705548'
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [string]$event.comment.body -ceq $required -and
  [int64]$event.comment.id -gt 6931739592) 'DISTINCT_OWNER_SOURCE_APPROVAL_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_OWNER_REQUIRED'
$t=Task
Need ([string]$t.State -cin @('Running','Ready') -and
  $t.Settings.Enabled -eq $true) 'ORIGINAL_TASK_NOT_RUNNING'
$database=Field $t 'Database'
$root=Field $t 'RepositoryRoot'
$python=Field $t 'PythonExe'
$wrapper=Field $t 'File'
Need ([IO.Path]::GetFullPath($database) -ieq
  [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite')) -and
  (Test-Path -LiteralPath $database -PathType Leaf) -and
  (Test-Path -LiteralPath $python -PathType Leaf) -and
  [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
  [IO.Path]::GetFullPath($root) -ieq
  [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$Source)))) 'ORIGINAL_DB_OR_SOURCE_ROUTE_DRIFT'
$checkout=(& git -C $env:GITHUB_WORKSPACE rev-parse HEAD | Out-String).Trim()
Need ($checkout -ceq $Main -and
  @(& git -C $env:GITHUB_WORKSPACE status --porcelain --untracked-files=all).Count -eq 0) 'WORKFLOW_SOURCE_DRIFT'
ExactSource
# Prove the immutable event1836 before we quiesce any process.
$pre=InvokeV50 'preflight'
Need ($pre.event_seq -eq 1836 -and
  $pre.source_sha -ceq $Source -and
  $pre.native_development_activated -eq $false -and
  $pre.scientific_first_use -eq $false -and
  $pre.job_count -eq 8) 'PRECOMMIT_CUSTODY_DRIFT'
try {
  # ONE authorized intervention on the existing task. Uncertain effect is
  # a forward-only hold; never replay a commit nor create another scheduler.
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $originalDisabled=$true
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
  $none=$false
  for($i=0;$i -lt 30;$i++){
    $held=Task
    if([string]$held.State -ceq 'Disabled' -and
       $held.Settings.Enabled -eq $false -and
       @(Children).Count -eq 0){$none=$true;break}
    Start-Sleep -Seconds 1
  }
  Need $none 'ORIGINAL_TASK_NOT_QUIESCED'
  ExactSource
  $activationAttempted=$true
  $result=InvokeV50 'commit'
  Need ($result.event_seq -eq 1837 -and
    $result.native_development_activated -eq $true -and
    $result.scientific_first_use -eq $false -and
    $result.new_dispatches -eq 0) 'EVENT1837_NOT_QUALIFIED'
  $held=Task
  Need ([string]$held.State -ceq 'Disabled' -and
    $held.Settings.Enabled -eq $false -and
    @(Children).Count -eq 0) 'POSTCOMMIT_TASK_NOT_QUIESCED'
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $originalDisabled=$false
  $one=$false
  for($i=0;$i -lt 30;$i++){
    $running=Task
    if($running.Settings.Enabled -eq $true -and
       [string]$running.State -cin @('Running','Ready') -and
       @(Children).Count -eq 1){$one=$true;break}
    Start-Sleep -Seconds 1
  }
  Need $one 'ORIGINAL_OWNER_PROCESS_NOT_LIVE'
  $verified=InvokeV50 'verify'
  Need ($verified.event_seq -eq 1837 -and
    $verified.native_development_activated -eq $true -and
    $verified.scientific_first_use -eq $false) 'POSTCOMMIT_LEDGER_READBACK_DRIFT'
  ExactSource
  Write-Host 'F139_V50_NATIVE_EVENT1837_COMMITTED=PASS'
  Write-Host 'F139_V50_SAME_ORIGINAL_OWNER_RESTARTED=PASS'
  Write-Host 'F139_V50_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Host 'F139_V50_NEW_CONTROLLER=FALSE'
} catch {
  # An ambiguous postcommit state must never be repeated, repaired by
  # rollback or treated as a successful restart.
  try {
    if($originalDisabled -or $activationAttempted) {
      Disable-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    }
  } catch {}
  throw ('F139_V50_FORWARD_ONLY_OWNER_HOLD_NO_REPLAY: '+$_.Exception.Message)
}
