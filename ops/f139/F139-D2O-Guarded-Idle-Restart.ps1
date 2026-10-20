# F139-D2O. Default: read-only preflight. -Apply: guarded controlled idle restart.
# Source SHA, owner, original custody and zero eligible work must all be proven.
[CmdletBinding()]
param([switch]$Apply)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Repo='spoonman136668-ai/FORGE'
$Main='34ca99c1b5b063225566082aee5aa180a15d093b'
$Seal='eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87'
$TaskName='FORGE-F139-UnifiedController'
$DB=Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite'
$Key=Join-Path $env:LOCALAPPDATA 'FORGE-F139\worker-hmac.dpapi.xml'
$Log=Join-Path $env:LOCALAPPDATA 'FORGE-F139\logs\controller.log'
$TaskEnabledByUs=$false;$TaskStartedByUs=$false;$Accepted=$false
function Need([bool]$ok,[string]$why){if(!$ok){throw ('F139_D2O_BLOCKED_'+$why)}}
function InvokeChecked([string]$program,[string[]]$args){
  $prior=$ErrorActionPreference
  try{$ErrorActionPreference='Continue';$output=@(& $program @args 2>&1);$code=$LASTEXITCODE}
  finally{$ErrorActionPreference=$prior}
  if($code -ne 0){
    $detail=(@($output|ForEach-Object{[string]$_}) -join ' ')
    if($detail.Length -gt 300){$detail=$detail.Substring(0,300)}
    throw ('F139_D2O_BLOCKED_NATIVE_'+$program+'_FAILED_'+$code+'_'+$detail)
  }
  return (@($output|ForEach-Object{[string]$_}) -join [Environment]::NewLine).Trim()
}
function API([string]$route){(InvokeChecked 'gh' @('api','-X','GET',$route))|ConvertFrom-Json}
function Identity{
  Need ($env:OS -ceq 'Windows_NT' -and $PSVersionTable.PSEdition -ceq 'Desktop') 'NATIVE_WINDOWS_REQUIRED'
  Need ($env:GITHUB_ACTIONS -cne 'true' -or ($env:GITHUB_REPOSITORY -ceq $Repo -and $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and $env:RUNNER_OS -ceq 'Windows')) 'WRONG_RUNNER'
  $u=[Security.Principal.WindowsIdentity]::GetCurrent()
  Need ($null -ne $u.User) 'WINDOWS_IDENTITY_ABSENT'
  $t=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  Need ($t.Principal.LogonType -ceq 'Interactive' -and $t.Principal.RunLevel -ceq 'Limited') 'TASK_SECURITY_DRIFT'
  $owner=if(([string]$t.Principal.UserId) -match '^S-1-') {
    [Security.Principal.SecurityIdentifier]::new([string]$t.Principal.UserId)
  } else {
    ([Security.Principal.NTAccount]::new([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier])
  }
  Need ($owner.Value -ceq $u.User.Value) 'NOT_TASK_OWNER'
  Need (@($t.Actions).Count -eq 1) 'TASK_ACTION_COUNT'
  $a=$t.Actions[0]
  Need ([IO.Path]::GetFileName([string]$a.Execute) -ieq 'powershell.exe') 'TASK_EXECUTABLE_DRIFT'
  Need ($a.Arguments -match '(?i)-WindowStyle\s+Hidden' -and $a.Arguments -match '(?i)-NonInteractive' -and $a.Arguments.Contains('Run-FORGE-F139.ps1')) 'TASK_ARGUMENT_DRIFT'
  $fields=@{}
  foreach($n in @('RepositoryRoot','Database','PythonExe','EncryptedKeyFile')){
    $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$n+'\s+"([^"]+)"')
    Need $m.Success ('TASK_MISSING_'+$n)
    $fields[$n]=$m.Groups[1].Value
  }
  Need ([IO.Path]::GetFullPath($fields.Database) -ieq [IO.Path]::GetFullPath($DB)) 'TASK_DATABASE_IDENTITY'
  Need ([IO.Path]::GetFullPath($fields.EncryptedKeyFile) -ieq [IO.Path]::GetFullPath($Key)) 'TASK_DPAPI_PATH'
  Need (Test-Path -LiteralPath $Key -PathType Leaf) 'OWNER_DPAPI_MISSING'
  Need (Test-Path -LiteralPath $fields.PythonExe -PathType Leaf) 'OWNER_PYTHON_MISSING'
  Need (Test-Path -LiteralPath (Join-Path $fields.RepositoryRoot 'f139\audit_d2k_custody.py') -PathType Leaf) 'QUALIFIED_AUDITOR_MISSING'
  Need ((InvokeChecked 'git' @('-C',$fields.RepositoryRoot,'rev-parse','HEAD')) -ceq $Main) 'TASK_SOURCE_NOT_MAIN'
  Need ([string]::IsNullOrWhiteSpace((InvokeChecked 'git' @('-C',$fields.RepositoryRoot,'status','--porcelain')))) 'TASK_SOURCE_DIRTY'
  $branch=API ('repos/'+$Repo+'/branches/main')
  Need ($branch.protected -eq $true -and $branch.commit.sha -ceq $Main) 'PROTECTED_MAIN_DRIFT'
  Need ((API 'user').login -ceq 'spoonman136668-ai') 'AUTH_OWNER_DRIFT'
  foreach($wf in @('forge-development-succession.yml','forge-integrated-synthetic-cycle.yml')){
    $item=API ('repos/'+$Repo+'/actions/workflows/'+$wf)
    Need ($item.state -ceq 'disabled_manually') 'LEGACY_GITHUB_ACTIVE'
    $runs=API ('repos/'+$Repo+'/actions/workflows/'+$wf+'/runs?per_page=100')
    Need (@($runs.workflow_runs|Where-Object {$_.status -in @('queued','in_progress','waiting','pending','requested')}).Count -eq 0) 'LEGACY_INFLIGHT'
  }
  Need ((Get-ScheduledTask -TaskName 'FORGE-F137-WakeProbe' -ErrorAction Stop).State -eq 'Disabled') 'LEGACY_F137_ACTIVE'
  return @{task=$t;fields=$fields}
}
function Children{
  @(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{
    $_.CommandLine -and $_.CommandLine.IndexOf($DB,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and
    $_.CommandLine -match '(?i)(f139[.\\/]local_controller|Run-FORGE-F139\.ps1)'
  })
}
function CaptureLog{
  if(!(Test-Path -LiteralPath $Log -PathType Leaf)){return ''}
  $fs=[IO.FileStream]::new($Log,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  try{$r=[IO.StreamReader]::new($fs);try{return $r.ReadToEnd()}finally{$r.Dispose()}}finally{$fs.Dispose()}
}
function Audit([hashtable]$binding){
  $code=@'
import json,sys,sqlite3
from pathlib import Path
from f139.audit_d2k_custody import audit
from f139.local_controller import GitHub
p,main,seal=sys.argv[1:]
proof=audit(Path(p),main,seal,qualified_main_sha=main)
assert proof['event_count']==24 and proof['source_only_suffix_count']==1,'EVENT_COUNT_DRIFT'
assert proof['live_main_source_suffix_verified'] is True,'PROTECTED_MAIN_PROOF_ABSENT'
assert proof['task_count']==4 and proof['archive_count']==8 and proof['d2j_task_bindings_verified']==2,'HISTORIC_CUSTODY_DRIFT'
assert proof['scientific_first_use'] is False and proof['original_database_writes']==0,'SCIENCE_OR_WRITES'
conn=sqlite3.connect(Path(p).as_uri()+'?mode=ro',uri=True)
try:
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    meta=dict(conn.execute('SELECT * FROM meta WHERE id=1').fetchone())
    tasks=[dict(x) for x in conn.execute('SELECT * FROM tasks ORDER BY ticket')]
    assert meta['source_sha']==main and meta['enabled']==1 and meta['legacy_suspended']==1 and meta['head_seq']==24,'CONTROLLER_STATE_DRIFT'
    assert len(tasks)==4 and all(t['stage']=='VERIFIED' for t in tasks),'PENDING_OR_UNVERIFIED_TASKS'
finally:conn.close()
eligible=GitHub().d2k_eligible_issues(main)
assert len(eligible)==0,'ELIGIBLE_WORK_PRESENT_NO_IDLE_RESTART'
print(json.dumps({'event_count':24,'task_count':4,'archive_count':8,'eligible_work':len(eligible),'science_authorized':False},sort_keys=True))
'@
  $old=(Get-Location).Path
  try{
    Set-Location -LiteralPath $binding.fields.RepositoryRoot
    $out=InvokeChecked $binding.fields.PythonExe @('-B','-c',$code,$DB,$Main,$Seal)
  }finally{Set-Location -LiteralPath $old}
  $report=$out|ConvertFrom-Json
  Need ($report.event_count -eq 24 -and $report.task_count -eq 4 -and $report.archive_count -eq 8 -and $report.eligible_work -eq 0 -and $report.science_authorized -eq $false) 'AUDIT_PROOF_INVALID'
}
try{
  $bound=Identity
  Need ($bound.task.State -eq 'Disabled') 'TASK_NOT_DISABLED'
  Need (@(Children).Count -eq 0) 'CONTROLLER_ALREADY_RUNNING'
  Audit $bound
  Write-Output 'F139_D2O_OWNER_IDENTITY_AND_LEGACY_ISOLATION=PASS'
  Write-Output 'F139_D2O_SOURCE_AND_24_EVENT_CUSTODY=PASS'
  Write-Output 'F139_D2O_IDLE_ADMISSION_ZERO_ELIGIBLE_WORK=PASS'
  if(!$Apply){
    Write-Output 'F139_D2O_DISPOSITION=READ_ONLY_RESTART_PREFLIGHT_PASS'
    return
  }
  $startLog=(CaptureLog).Length
  $bound=Identity
  Need ($bound.task.State -eq 'Disabled') 'TASK_MOVED_BEFORE_START'
  Need (@(Children).Count -eq 0) 'CONTROLLER_STARTED_UNEXPECTEDLY'
  Audit $bound
  Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
  $TaskEnabledByUs=$true
  Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $TaskStartedByUs=$true
  $idle=$false
  for($i=0;$i -lt 110;$i++){
    $t=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $kids=@(Children)
    Need ($kids.Count -le 2) 'MULTIPLE_CONTROLLER_PROCESSES'
    $txt=CaptureLog
    Need ($txt.Length -ge $startLog) 'CONTROLLER_LOG_TRUNCATED'
    $tail=$txt.Substring($startLog)
    Need (-not ($tail -match '(?i)(F139_FAIL_CLOSED|MAIN_SOURCE_DRIFT|F139_JOB_SUPERVISOR_BLOCKED|DEVELOPMENT_DISPATCHED_ONCE)')) 'START_LOG_REJECTION_OR_DISPATCH'
    if($t.State -eq 'Running' -and $kids.Count -ge 1 -and $tail.Contains('QUEUE_EMPTY_NO_SCIENCE')){
      $idle=$true
      break
    }
    Start-Sleep -Milliseconds 500
  }
  Need $idle 'CONTROLLER_DID_NOT_PROVE_IDLE'
  Audit (Identity)
  Need ((Get-ScheduledTask -TaskName $TaskName).State -eq 'Running') 'TASK_NOT_RUNNING'
  Need (@(Children).Count -ge 1) 'CONTROLLER_CHILD_MISSING'
  $Accepted=$true
  Write-Output 'F139_D2O_CONTROLLER_RUNNING_IN_EXISTING_TASK=PASS'
  Write-Output 'F139_D2O_IDLE_POLL_NO_NEW_DISPATCH=PASS'
  Write-Output 'F139_D2O_24_EVENT_LEDGER_AND_ORIGINALS_UNCHANGED=PASS'
  Write-Output 'F139_D2O_SCIENTIFIC_FIRST_USE=BLOCKED'
  Write-Output 'F139_D2O_DISPOSITION=QUALIFIED_IDLE_CONTROLLER_RESTART_PASS'
}catch{
  Write-Output ('F139_D2O_BLOCKED='+$_.Exception.Message)
  if(($TaskEnabledByUs -or $TaskStartedByUs) -and !$Accepted){
    try{Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null}catch{}
    try{Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue}catch{}
    Write-Output 'F139_D2O_FAIL_CLOSED_CONTROLLER_DISABLED=ATTEMPTED'
  }
  throw
}
