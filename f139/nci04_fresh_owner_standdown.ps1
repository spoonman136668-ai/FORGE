# F139 one-shot original Windows owner standdown, never rebind or dispatch.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Name='FORGE-F139-UnifiedController'
$Old='c06403c8b6035c6c7013866a7ea08cef1244b507'
$ExpectedHead='e10be7151e19f2104ef2659ae04bef89b2711eea1659decb1477fd7354ff24ec'
$Repo='spoonman136668-ai/FORGE'
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('F139_FRESH_OWNER_STANDDOWN_'+$code)}}
function GetArg($Task,[string]$Key){
  $m=[regex]::Match([string]$Task.Actions[0].Arguments,'(?i)(?:^|\s)-'+$Key+'\s+"([^"]+)"')
  Need $m.Success ('ARG_'+$Key)
  return [string]$m.Groups[1].Value
}
function Controllers {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
}
Need ($env:GITHUB_REPOSITORY -ceq $Repo -and $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $Target -cmatch '^[a-f0-9]{40}$' -and $Target -ceq $env:GITHUB_SHA -and
  -not $env:OPENAI_API_KEY -and $env:GH_TOKEN) 'OWNER_RUNNER_AUTHORITY'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
$expected='F139-FRESH-DEV-OWNER-STANDDOWN '+$Target
Need ($event.action -ceq 'created' -and $event.issue.number -eq 1830 -and
  $event.issue.state -ceq 'open' -and $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  $event.comment.body -ceq $expected -and [int64]$event.comment.id -gt 0) 'OWNER_COMMENT_INVALID'
$remote=(& gh api ('repos/'+$Repo+'/issues/comments/'+[string]$event.comment.id) | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and [int64]$remote.id -eq [int64]$event.comment.id -and
  $remote.user.login -ceq 'spoonman136668-ai' -and
  $remote.author_association -ceq 'OWNER' -and $remote.body -ceq $expected -and
  $remote.created_at -ceq $event.comment.created_at) 'OWNER_COMMENT_REMOTE_DRIFT'
$main=(& gh api ('repos/'+$Repo+'/branches/main') | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and $main.protected -eq $true -and
  $main.commit.sha -ceq $Target -and
  (& git rev-parse HEAD | Out-String).Trim() -ceq $Target -and
  @(& git status --porcelain --untracked-files=all).Count -eq 0) 'SOURCE_MOVED'
$policyIssue=(& gh api ('repos/'+$Repo+'/issues/807') | ConvertFrom-Json)
$policy=[string]$policyIssue.body | ConvertFrom-Json
Need ($LASTEXITCODE -eq 0 -and $policyIssue.state -ceq 'open' -and
  $policy.source_sha -ceq $Old -and $policy.scientific_first_use -eq $false -and
  $policy.paid_model_calls -eq 0 -and $policy.new_controller -eq $false -and
  $policy.new_scheduler -eq $false) 'ORIGINAL_POLICY_DRIFT'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'OWNER_ADMIN_REQUIRED'
$task=Get-ScheduledTask -TaskName $Name -ErrorAction Stop
$OriginalArguments=[string]$task.Actions[0].Arguments
$sid=''
try {$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
  Translate([Security.Principal.SecurityIdentifier]).Value} catch {}
Need ([string]$task.State -cin @('Running','Ready') -and
  $task.Settings.Enabled -eq $true -and
  @($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
  ([string]$task.Principal.UserId -ieq $identity.Name -or $sid -ceq $identity.User.Value) -and
  [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe' -and
  [string]$task.Actions[0].Arguments -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') 'ORIGINAL_TASK_IDENTITY'
$root=GetArg $task 'RepositoryRoot'
$database=GetArg $task 'Database'
$python=GetArg $task 'PythonExe'
$wrapper=GetArg $task 'File'
$expectedDb=Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite'
$expectedRoot=Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$Old)
Need ([IO.Path]::GetFullPath($database) -ieq [IO.Path]::GetFullPath($expectedDb) -and
  [IO.Path]::GetFullPath($root) -ieq [IO.Path]::GetFullPath($expectedRoot) -and
  [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
  (Test-Path -LiteralPath $python -PathType Leaf) -and
  (Test-Path -LiteralPath $database -PathType Leaf) -and
  (& git -C $root rev-parse HEAD | Out-String).Trim() -ceq $Old -and
  @(& git -C $root status --porcelain --untracked-files=all).Count -eq 0) 'INSTALLED_ORIGINAL_DRIFT'
$beforeProcesses=@(Controllers)
Need ($beforeProcesses.Count -le 1 -and
  @($beforeProcesses | Where-Object {
    $_.CommandLine.IndexOf($database,[StringComparison]::OrdinalIgnoreCase) -lt 0
  }).Count -eq 0) 'DUPLICATE_OR_FOREIGN_CONTROLLER'
Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
$lease=$null
try {
  $lease=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($database,'.lock'),120000)
  $code=@'
from pathlib import Path
import json,sys
from f139.local_controller import Database
from f139.nci04_v59_owner_forward_readiness import audit_frozen_original_readonly
db=Database.open_readonly(Path(sys.argv[1]))
try:
  report=audit_frozen_original_readonly(db)
  assert report["head_seq"]==1864 and report["head_sha256"]==sys.argv[2]
  assert db.conn.total_changes==0
  print("F139_STANDDOWN_ORIGINAL_LEDGER="+json.dumps({"head_seq":report["head_seq"],"head_sha256":report["head_sha256"]},sort_keys=True))
finally:
  db.close()
'@
  $ledgerBefore=@($code | & $python -B - $database $ExpectedHead)
  Need ($LASTEXITCODE -eq 0 -and $ledgerBefore.Count -eq 1 -and
    $ledgerBefore[0] -cmatch '^F139_STANDDOWN_ORIGINAL_LEDGER=') 'ORIGINAL_LEDGER_PREFLIGHT'
  $task=Get-ScheduledTask -TaskName $Name -ErrorAction Stop
  Need ($task.Settings.Enabled -eq $true -and
    @($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
    [string]$task.Actions[0].Arguments -ceq $OriginalArguments) 'TASK_MOVED'
  Disable-ScheduledTask -TaskName $Name -ErrorAction Stop | Out-Null
  if([string]$task.State -ceq 'Running') {
    Stop-ScheduledTask -TaskName $Name -ErrorAction Stop | Out-Null
  }
  for($i=0;$i -lt 40;$i++){
    if(@(Controllers).Count -eq 0){break}
    Start-Sleep -Seconds 1
  }
  $after=Get-ScheduledTask -TaskName $Name -ErrorAction Stop
  Need ([string]$after.State -ceq 'Disabled' -and
    $after.Settings.Enabled -eq $false -and
    @(Controllers).Count -eq 0) 'ORIGINAL_OWNER_NOT_QUIESCED'
  $ledgerAfter=@($code | & $python -B - $database $ExpectedHead)
  Need ($LASTEXITCODE -eq 0 -and $ledgerAfter.Count -eq 1 -and
    $ledgerAfter[0] -ceq $ledgerBefore[0]) 'ORIGINAL_LEDGER_CHANGED'
  Write-Output 'F139_FRESH_DEV_OWNER_STANDDOWN=PASS'
  Write-Output 'F139_ORIGINAL_EVENT1864_PRESERVED=PASS'
  Write-Output 'F139_ORIGINAL_TASK_DISABLED=PASS'
  Write-Output 'F139_ORIGINAL_CONTROLLER_PROCESSES=ZERO'
  Write-Output 'F139_WORKER_DISPATCH_AUTHORIZED=FALSE'
  Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
} finally {
  if($lease){$lease.Dispose()}
}
