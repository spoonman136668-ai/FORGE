# Rebind ONLY existing disabled FORGE-F139-UnifiedController to admitted fresh DEV.
# Never enable/start another task, dispatch a worker, call a model or replay old SQLite.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Repo='spoonman136668-ai/FORGE'
$Old='c06403c8b6035c6c7013866a7ea08cef1244b507'
$Fresh='408139c0a10fd4836a22422c8df041aa64dfa001'
$FreshTree='4f35d3965bfd2d8688586600926445008e16f5b9'
$FreshRun=44831323193
$FreshHead='b099aba6750a4ae323ffd5291ea0ae940b1403b4063aa89f34521fe513383337'
$TaskName='FORGE-F139-UnifiedController'
$Prefix='F139-FRESH-DEV-TASK-REBIND '
function Need([bool]$ok,[string]$why) {
  if(-not $ok) {throw ('F139_FRESH_OWNER_REBIND_'+$why)}
}
function OriginalTask {
  return Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
}
function GetArg($task,[string]$name) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
                    '(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  Need $m.Success ('ORIGINAL_ARG_'+$name)
  return [string]$m.Groups[1].Value
}
function Controllers {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
}
function CheckDisabled($task) {
  Need ($null -ne $task -and @($task.Actions).Count -eq 1 -and
    @($task.Triggers).Count -eq 3 -and [string]$task.State -ceq 'Disabled' -and
    $task.Settings.Enabled -eq $false) 'SINGLE_DISABLED_ORIGINAL_TASK_REQUIRED'
}
function CheckSource([string]$folder,[string]$expected,[string]$tree) {
  Need (Test-Path -LiteralPath $folder -PathType Container) 'REPO_NOT_INSTALLED'
  $head=(& git -C $folder rev-parse HEAD | Out-String).Trim()
  $actualTree=(& git -C $folder rev-parse 'HEAD^{tree}' | Out-String).Trim()
  $dirty=@(& git -C $folder status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $head -ceq $expected -and
    $actualTree -ceq $tree -and $dirty.Count -eq 0) 'INSTALLED_GIT_SHA_TREE_DIRTY'
}
Need ($env:GITHUB_REPOSITORY -ceq $Repo -and $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_WORKFLOW_REF -ceq ($Repo+'/.github/workflows/f139-fresh-original-owner-rebind.yml@refs/heads/main') -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $Target -cmatch '^[a-f0-9]{40}$' -and $Target -ceq $env:GITHUB_SHA -and
  $env:GH_TOKEN -and -not $env:OPENAI_API_KEY) 'EXISTING_OWNER_WORKFLOW_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'OWNER_ADMIN_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_EVENT_PATH -PathType Leaf) 'OWNER_EVENT_MISSING'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
$expected=$Prefix+$Target+' '+[string]$FreshRun
Need ($event.action -ceq 'created' -and $event.issue.number -eq 1830 -and
  $event.issue.state -ceq 'open' -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  $event.comment.body -ceq $expected -and
  [int64]$event.comment.id -gt 0) 'OWNER_SOURCE_BOUND_COMMENT_REQUIRED'
$remote=(& gh api ('repos/'+$Repo+'/issues/comments/'+[string]$event.comment.id) | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and
  [int64]$remote.id -eq [int64]$event.comment.id -and
  $remote.user.login -ceq 'spoonman136668-ai' -and
  $remote.author_association -ceq 'OWNER' -and
  $remote.body -ceq $expected -and
  $remote.created_at -ceq $event.comment.created_at) 'COMMENT_PROVIDER_READBACK_DRIFT'
$main=(& gh api ('repos/'+$Repo+'/branches/main') | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and $main.protected -eq $true -and
  $main.commit.sha -ceq $Target -and
  (& git rev-parse HEAD | Out-String).Trim() -ceq $Target -and
  @(& git status --porcelain --untracked-files=all).Count -eq 0) 'PROTECTED_MAIN_OR_CHECKOUT_DRIFT'
$pr=(& gh api ('repos/'+$Repo+'/pulls/1851') | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and $pr.merged -eq $true -and
  $pr.state -ceq 'closed' -and $pr.merge_commit_sha -ceq $Target -and
  $pr.head.ref -ceq 'engineering/f139-fresh-original-task-rebind-20261120' -and
  $pr.base.repo.full_name -ceq $Repo -and
  $pr.user.login -ceq 'spoonman136668-ai') 'QUALIFIED_OWNER_SOURCE_PR_REQUIRED'
$release=(& gh api ('repos/'+$Repo+'/branches/f139-owner-release-'+$Fresh) | ConvertFrom-Json)
Need ($LASTEXITCODE -eq 0 -and $release.protected -eq $true -and
  $release.commit.sha -ceq $Fresh) 'IMMUTABLE_WORKER_RELEASE_NOT_PRESENT'
$policyIssue=(& gh api ('repos/'+$Repo+'/issues/807') | ConvertFrom-Json)
$policy=[string]$policyIssue.body | ConvertFrom-Json
Need ($LASTEXITCODE -eq 0 -and $policyIssue.state -ceq 'open' -and
  $policy.source_sha -ceq $Old -and $policy.enabled -eq $true -and
  $policy.scientific_first_use -eq $false -and
  $policy.paid_model_calls -eq 0 -and $policy.new_scheduler -eq $false -and
  $policy.new_controller -eq $false -and $policy.new_queue -eq $false) 'ORIGINAL_OWNER_POLICY_CHANGED'
$task=OriginalTask
CheckDisabled $task
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
} catch {}
Need ([string]$task.Principal.UserId -ieq $who.Name -or
  $sid -ceq $who.User.Value) 'ORIGINAL_TASK_SID_DRIFT'
Need ([IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe' -and
  [string]$task.Actions[0].Arguments -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') 'ORIGINAL_ACTION_DRIFT'
$oldRoot=GetArg $task 'RepositoryRoot'
$oldDb=GetArg $task 'Database'
$oldPy=GetArg $task 'PythonExe'
$oldWrapper=GetArg $task 'File'
$profile=$env:LOCALAPPDATA
Need ([IO.Path]::GetFullPath($oldRoot) -ieq
  [IO.Path]::GetFullPath((Join-Path $profile ('FORGE-F139\release-candidates\'+$Old))) -and
  [IO.Path]::GetFullPath($oldDb) -ieq
  [IO.Path]::GetFullPath((Join-Path $profile 'FORGE-F139\state.sqlite')) -and
  [IO.Path]::GetFileName($oldWrapper) -ceq 'Run-FORGE-F139.ps1' -and
  (Test-Path -LiteralPath $oldPy -PathType Leaf) -and
  (Test-Path -LiteralPath $oldDb -PathType Leaf)) 'OLD_OWNER_INSTALL_PATH_CHANGED'
CheckSource $oldRoot $Old 'b7abf26f618654f330b55f510bfcc34d8916848a'
Need (@(Controllers).Count -eq 0) 'ACTIVE_OR_FOREIGN_CONTROLLER'
$freshDb=Join-Path $profile ('FORGE-F139\f139-fresh-dev-'+[string]$FreshRun+'\state.sqlite')
Need (Test-Path -LiteralPath $freshDb -PathType Leaf) 'ACTIVATED_FRESH_SQLITE_NOT_FOUND'
$receipt=Join-Path (Split-Path -Parent $freshDb) 'fresh-owner-task-rebind.json'
Need (-not (Test-Path -LiteralPath $receipt)) 'REBINDED_OR_UNKNOWN_ATTEMPT_NO_REPLAY'
Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
$mutexOld=$null
$mutexFresh=$null
try {
  $mutexOld=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($oldDb,'.lock'),120000)
  $mutexFresh=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($freshDb,'.lock'),120000)
  CheckDisabled (OriginalTask)
  Need (@(Controllers).Count -eq 0) 'CONTROLLER_STARTED_DURING_REBIND'
  $program=@'
import json,sys
from pathlib import Path
from f139.local_controller import Database
from f139.nci04_fresh_native_owner_route import inspect_staged_fresh_native_mode
from f139.nci04_v59_owner_forward_readiness import audit_frozen_original_readonly
old, fresh = Path(sys.argv[1]), Path(sys.argv[2])
original = Database.open_readonly(old)
try:
    original.verify()
    frozen = audit_frozen_original_readonly(original)
    assert frozen["source_sha"] == "c06403c8b6035c6c7013866a7ea08cef1244b507"
    assert frozen["head_seq"] == 1864
    assert original.conn.total_changes == 0
finally:
    original.close()
new = Database.open_readonly(fresh)
try:
    new.verify()
    meta = new.meta()
    mode = inspect_staged_fresh_native_mode(new, fresh)
    assert meta["source_sha"] == "408139c0a10fd4836a22422c8df041aa64dfa001"
    assert meta["head_seq"] == 4
    assert meta["head_hash"] == "b099aba6750a4ae323ffd5291ea0ae940b1403b4063aa89f34521fe513383337"
    assert mode["disposition"] == "FRESH_DEVELOPMENT_INTAKE_READY_DISPATCH_BLOCKED"
    assert mode["fresh_work_admitted"] is True
    assert mode["worker_dispatched"] is False
    assert new.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage='READY'").fetchone()[0] == 1
    assert new.conn.total_changes == 0
finally:
    new.close()
print("F139_FRESH_OLD_1864_AND_NEW_READY_EVENT4=PASS")
'@
  $env:PYTHONPATH=$env:GITHUB_WORKSPACE
  $read=@($program | & $oldPy -B - $oldDb $freshDb)
  Need ($LASTEXITCODE -eq 0 -and $read.Count -eq 1 -and
    $read[0] -ceq 'F139_FRESH_OLD_1864_AND_NEW_READY_EVENT4=PASS') 'COLD_DB_CUSTODY_OR_TASK_NOT_READY'
  $stage=Join-Path $profile ('FORGE-F139\release-candidates\'+$Fresh)
  Need (-not (Test-Path -LiteralPath $stage)) 'SOURCE_INSTALL_ATTEMPT_ALREADY_EXISTS'
  Need ((& git -C $env:GITHUB_WORKSPACE cat-file -t $Fresh | Out-String).Trim() -ceq 'commit') 'FRESH_RELEASE_SOURCE_NOT_LOCAL'
  & git clone --no-local --no-checkout --quiet -- $env:GITHUB_WORKSPACE $stage
  Need ($LASTEXITCODE -eq 0) 'CREATE_ONLY_SOURCE_CLONE_FAILED'
  & git -C $stage checkout --quiet --detach $Fresh
  Need ($LASTEXITCODE -eq 0) 'SOURCE_CLONE_CHECKOUT_FAILED'
  & git -C $stage remote remove origin
  Need ($LASTEXITCODE -eq 0) 'SOURCE_CLONE_REMOTE_REMOVAL_FAILED'
  CheckSource $stage $Fresh $FreshTree
  Need ((& git -C $stage remote | Out-String).Trim() -ceq '' -and
    (Test-Path -LiteralPath (Join-Path $stage 'scripts/Run-FORGE-F139.ps1') -PathType Leaf)) 'EXACT_STAGED_SOURCE_INCOMPLETE'
  $originalArguments=[string]$task.Actions[0].Arguments
  Need ($originalArguments.Split(@($oldRoot),[StringSplitOptions]::None).Count -eq 3 -and
    $originalArguments.Split(@($oldDb),[StringSplitOptions]::None).Count -eq 2) 'ORIGINAL_ACTION_NOT_EXACTLY_REPLACEABLE'
  $newArgs=$originalArguments.Replace($oldRoot,$stage).Replace($oldDb,$freshDb)
  Need ($newArgs -cne $originalArguments -and
    $newArgs.Contains($freshDb) -and $newArgs.Contains($stage) -and
    -not $newArgs.Contains($oldDb) -and -not $newArgs.Contains($oldRoot)) 'REBOUND_ACTION_NOT_EXACT'
  $oldAction=$task.Actions[0]
  $work=[string]$oldAction.WorkingDirectory
  if ($work -ieq $oldRoot) {$work=$stage}
  $newAction=if($work) {
    New-ScheduledTaskAction -Execute ([string]$oldAction.Execute) -Argument $newArgs -WorkingDirectory $work
  } else {
    New-ScheduledTaskAction -Execute ([string]$oldAction.Execute) -Argument $newArgs
  }
  Need (@(Controllers).Count -eq 0) 'CONTROLLER_UNEXPECTEDLY_REAPPEARED'
  CheckDisabled (OriginalTask)
  # ONE-SHOT existing task action update. NO Enable/Start/other task writes.
  Set-ScheduledTask -TaskName $TaskName -Action $newAction -ErrorAction Stop | Out-Null
  $actual=OriginalTask
  CheckDisabled $actual
  Need (@(Controllers).Count -eq 0 -and
    [string]$actual.Actions[0].Arguments -ceq $newArgs -and
    [string]$actual.Principal.UserId -ceq [string]$task.Principal.UserId -and
    @($actual.Triggers).Count -eq 3) 'ORIGINAL_DISABLED_TASK_REBIND_READBACK_FAILED'
  $json=@{
    schema='forge.f139.fresh-existing-task-rebound-disabled.v1'
    source_sha=$Fresh
    owner_workflow_source_sha=$Target
    owner_run_id=[int64]$env:GITHUB_RUN_ID
    fresh_activation_run_id=[int64]$FreshRun
    new_database_path=$freshDb
    task_name=$TaskName
    original_head_seq=1864
    fresh_head_seq=4
    fresh_head_sha256=$FreshHead
    existing_task_only=$true
    task_disabled=$true
    worker_dispatched=$false
    scientific_first_use=$false
    model_continuation_authorized=$false
    paid_model_calls=0
    original_sqlite_mutations=0
  } | ConvertTo-Json -Compress -Depth 5
  $utf8=New-Object System.Text.UTF8Encoding($false)
  $stream=[IO.File]::Open($receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try {
    $data=$utf8.GetBytes([string]$json)
    $stream.Write($data,0,$data.Length)
    $stream.Flush($true)
  } finally {$stream.Dispose()}
  Write-Output 'F139_FRESH_EXISTING_DISABLED_TASK_REBIND=PASS'
  Write-Output 'F139_FRESH_ORIGINAL_1864_PRESERVED=PASS'
  Write-Output 'F139_FRESH_EVENT4_READY_PRESERVED=PASS'
  Write-Output 'F139_FRESH_WORKER_DISPATCH=FALSE'
  Write-Output 'F139_FRESH_SCIENTIFIC_FIRST_USE=FALSE'
} finally {
  if ($null -ne $mutexFresh) {$mutexFresh.Dispose()}
  if ($null -ne $mutexOld) {$mutexOld.Dispose()}
}
