# Restore original F139 owner only after proven V53 precommit failure.
param([Parameter(Mandatory=$true)][string]$Main)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$name='FORGE-F139-UnifiedController'
$old='2ea68f93cbe6323aa6b0cbe99e47a32f0717b04c'
$head='376fe4921a41374ff47b1779c7d625bc3677ace91a052d6b64c790e390677c70'
$failedRun=44095406266L
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('F139_V53_RESTORE_'+$code)}}
function GetJson([string]$route){
  Need ($route.StartsWith('repos/spoonman136668-ai/FORGE/')) 'UNSCOPED_GET'
  for($i=0;$i -lt 2;$i++){
    $out=@(& gh api $route)
    if($LASTEXITCODE -eq 0 -and $out.Count -gt 0){
      return (($out -join [Environment]::NewLine)|ConvertFrom-Json -Depth 32)
    }
    if($i -eq 0){Start-Sleep -Seconds 2}
  }
  throw 'F139_V53_RESTORE_GITHUB_GET_FAILED'
}
function Field($task,[string]$key){
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success ('ORIGINAL_TASK_ARG_'+$key)
  return [string]$m.Groups[1].Value
}
function Children {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
}
function GitSource([string]$path){
  $sha=(& git -C $path rev-parse HEAD | Out-String).Trim()
  $dirty=@(& git -C $path status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'ORIGINAL_SOURCE_DIRTY'
  return $sha
}
Need ($env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issues' -and
  $env:GITHUB_WORKFLOW_REF -ceq 'spoonman136668-ai/FORGE/.github/workflows/f139-v53-precommit-owner-restore.yml@refs/heads/main' -and
  $env:GITHUB_JOB -ceq 'restore-original-owner' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:GITHUB_SHA -ceq $Main -and
  $Main -cmatch '^[a-f0-9]{40}$' -and
  -not $env:OPENAI_API_KEY) 'ORIGINAL_OWNER_RUNNER_AUTHORITY'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json -Depth 20
Need ($event.action -ceq 'unassigned' -and
  $event.repository.full_name -ceq 'spoonman136668-ai/FORGE' -and
  $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $event.issue.state -ceq 'open' -and
  $event.assignee.login -ceq 'spoonman136668-ai' -and
  $event.sender.login -ceq 'spoonman136668-ai') 'OWNER_UNASSIGNMENT_AUTHORITY'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($who).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_OWNER_ADMIN'
Need ((GitSource $env:GITHUB_WORKSPACE) -ceq $Main) 'CHECKOUT_SOURCE_DRIFT'
$run=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$env:GITHUB_RUN_ID)
Need ($run.name -ceq 'FORGE F139 V53 original precommit owner restore' -and
  $run.path -ceq '.github/workflows/f139-v53-precommit-owner-restore.yml' -and
  $run.event -ceq 'issues' -and
  $run.actor.login -ceq 'spoonman136668-ai' -and
  $run.head_sha -ceq $Main -and $run.head_branch -ceq 'main' -and
  $run.run_attempt -eq 1 -and $run.status -ceq 'in_progress' -and
  $null -eq $run.conclusion) 'ORIGINAL_RUN_IDENTITY'
$branch=GetJson 'repos/spoonman136668-ai/FORGE/branches/main'
Need ($branch.protected -eq $true -and $branch.commit.sha -ceq $Main) 'PROTECTED_MAIN_DRIFT'
$runs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs?head_sha='+$Main+'&event=push&branch=main&per_page=100')
$q=@($runs.workflow_runs|Where-Object {$_.name -ceq 'FORGE public Linux and Windows qualification'})
Need ($q.Count -eq 1 -and $q[0].status -ceq 'completed' -and
  $q[0].conclusion -ceq 'success' -and $q[0].head_sha -ceq $Main -and
  $q[0].run_attempt -eq 1 -and
  $q[0].actor.login -ceq 'spoonman136668-ai') 'FULL_MAIN_CI_NOT_PASS'
$jobs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$q[0].id+'/jobs?per_page=100')
$expected=@('linux_genenv','linux_native','linux_f139','windows_genenv','windows_native','windows_f139','linux','windows')
Need ($jobs.total_count -eq 8 -and @($jobs.jobs).Count -eq 8 -and
  @($jobs.jobs|Where-Object {$_.status -ceq 'completed' -and $_.conclusion -ceq 'success'}).Count -eq 8 -and
  @($jobs.jobs|Where-Object {$expected -contains $_.name}).Count -eq 8) 'FULL_EIGHT_JOB_REGRESSION'
$prior=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$failedRun)
Need ($prior.id -eq $failedRun -and $prior.event -ceq 'issues' -and
  $prior.head_sha -ceq '918a7a10a3f47e30b2ecd6d3d443ff16428b9c0b' -and
  $prior.actor.login -ceq 'spoonman136668-ai' -and
  $prior.run_attempt -eq 1 -and $prior.status -ceq 'completed' -and
  $prior.conclusion -ceq 'failure') 'FAILED_PRECOMMIT_RUN_IDENTITY'
$failedJobs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$failedRun+'/jobs?per_page=100')
$rehearsal=@($failedJobs.jobs|Where-Object {$_.name -ceq 'detached-owner-rehearsal'})
$live=@($failedJobs.jobs|Where-Object {$_.name -ceq 'original-owner-forward-repair'})
Need ($failedJobs.total_count -eq 2 -and $rehearsal.Count -eq 1 -and
  $live.Count -eq 1 -and
  $rehearsal[0].conclusion -ceq 'success' -and
  $live[0].conclusion -ceq 'failure' -and
  $rehearsal[0].runner_name -ceq 'FORGE-CODEX-REMOTE' -and
  $live[0].runner_name -ceq 'FORGE-CODEX-REMOTE') 'FAILED_RUN_JOB_PROVENANCE'
$issue=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
$policy=[string]$issue.body|ConvertFrom-Json -Depth 20
Need ($issue.state -ceq 'open' -and $issue.user.login -ceq 'spoonman136668-ai' -and
  @($issue.assignees).Count -eq 0 -and
  $policy.source_sha -ceq $old -and $policy.enabled -eq $true -and
  @($policy.lanes).Count -eq 3 -and
  $policy.lanes[0] -ceq 'Wingless' -and
  $policy.lanes[1] -ceq 'Yggdrasil' -and
  $policy.lanes[2] -ceq 'TTT-Hybrid' -and
  $policy.scientific_first_use -eq $false -and
  $policy.new_controller -eq $false -and
  $policy.new_scheduler -eq $false -and
  $policy.new_queue -eq $false -and
  $policy.paid_model_calls -eq 0) 'ORIGINAL_POLICY_PRECOMMIT'
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
}catch{}
Need (@($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
  ([string]$task.Principal.UserId -ieq $who.Name -or
   $sid -ceq $who.User.Value) -and
  [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe' -and
  [string]$task.State -ceq 'Disabled' -and
  $task.Settings.Enabled -eq $false) 'EXACT_ORIGINAL_DISABLED_TASK'
$script:database=Field $task 'Database'
$root=Field $task 'RepositoryRoot'
$python=Field $task 'PythonExe'
$wrapper=Field $task 'File'
$originalArgs=[string]$task.Actions[0].Arguments
Need ([IO.Path]::GetFullPath($database) -ieq
    [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite')) -and
  [IO.Path]::GetFullPath($root) -ieq
    [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$old))) -and
  [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
  (Test-Path -LiteralPath $database -PathType Leaf) -and
  (Test-Path -LiteralPath $python -PathType Leaf) -and
  (GitSource $root) -ceq $old -and
  @(Children).Count -eq 0) 'EXACT_ORIGINAL_SOURCE_OR_PROCESS'
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
$lines=@(& $python -B -m f139.nci04_v53_owner_forward_repair_cli --mode preflight --db $database)
Need ($LASTEXITCODE -eq 0 -and @($lines).Count -eq 1 -and
  [string]$lines[0] -clike 'F139_V53_PREFLIGHT=*') 'READONLY_ORIGINAL_DB_PREFLIGHT'
$report=([string]$lines[0]).Substring('F139_V53_PREFLIGHT='.Length)|ConvertFrom-Json -Depth 20
Need ($report.source_sha -ceq $old -and $report.head_seq -eq 1839 -and
  $report.head_sha256 -ceq $head -and
  [string]$report.terminal_tasks_sha256 -cmatch '^[a-f0-9]{64}$') 'EVENT1839_PRECOMMIT_DRIFT'
Need ((Get-ScheduledTask -TaskName $name).State -ceq 'Disabled' -and
  @(Children).Count -eq 0 -and (GitSource $root) -ceq $old) 'PRESTART_DRIFT'
# The ONLY mutations: re-enable and restart the SAME existing task.
Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
$started=$false
for($i=0;$i -lt 30;$i++){
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  if($t.Settings.Enabled -eq $true -and
     [string]$t.State -cin @('Running','Ready') -and
     [string]$t.Actions[0].Arguments -ceq $originalArgs -and
     @(Children).Count -eq 1){$started=$true;break}
  Start-Sleep -Seconds 1
}
Need $started 'ORIGINAL_OWNER_RESTART_UNVERIFIED'
$check=@'
import json,sys
from pathlib import Path
from f139.local_controller import Database
from f139.nci04_owner_ledger import verify_native_activation
db=Database.open_readonly(Path(sys.argv[1]).resolve())
try:
    db.verify()
    m=db.meta()
    assert m["source_sha"]==sys.argv[2] and m["head_seq"]>=1839
    assert m["enabled"]==1 and m["legacy_suspended"]==1
    assert verify_native_activation(db) is True
    print("F139_V53_RESTORED_READONLY="+json.dumps({"source_sha":m["source_sha"],"head_seq":m["head_seq"],"head_hash":m["head_hash"],"scientific_first_use":False},sort_keys=True))
finally:
    db.close()
'@
$post=@($check|& $python -B - $database $old)
Need ($LASTEXITCODE -eq 0 -and $post.Count -eq 1 -and
  [string]$post[0] -clike 'F139_V53_RESTORED_READONLY=*' -and
  (GitSource $root) -ceq $old) 'POSTSTART_ORIGINAL_EVIDENCE'
Write-Output ('F139_V53_ORIGINAL_PRECOMMIT_RESTORED='+([string]$post[0]).Substring('F139_V53_RESTORED_READONLY='.Length))
Write-Output 'F139_V53_SAME_ORIGINAL_OWNER_RESTORED=PASS'
Write-Output 'F139_V53_ORIGINAL_SOURCE_TRANSITION_REPLAY=FALSE'
Write-Output 'F139_V53_NEW_CONTROLLER=FALSE'
