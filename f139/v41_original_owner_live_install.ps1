# One-shot original-owner V40 -> V41 cutover; only after exact approval+backup.
# Never restore precommit SQLite after SOURCE_TRANSITION_ADMITTED.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$old='2c7caad5a4502d4b874a11d57207a35cf033eb08'
$name='FORGE-F139-UnifiedController'
$disabled=$false
$commitEntered=$false
$activated=$false
$originalArgs=$null
$originalRoot=$null
$originalPolicy=$null
$database=$null
$python=$null
function Need([bool]$ok,[string]$code) {
  if(-not $ok){throw ('F139_V41_LIVE_INSTALL_'+$code)}
}
function OwnerArg($task,[string]$key) {
  $match=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $match.Success ('ORIGINAL_TASK_ARG_'+$key)
  return $match.Groups[1].Value
}
function ReadPolicy {
  $raw=@(& gh api repos/spoonman136668-ai/FORGE/issues/807 --jq '.body')
  Need ($LASTEXITCODE -eq 0 -and $raw.Count -eq 1) 'OWNER_POLICY_READ'
  return [string]$raw[0]
}
function ReadSource([string]$folder) {
  $sha=(& git -C $folder rev-parse HEAD | Out-String).Trim()
  $dirty=@(& git -C $folder status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'SOURCE_NOT_CLEAN'
  return $sha
}
function Children {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object {$_.CommandLine -and $null -ne $database -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
}
function Disabled {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$t.State -ceq 'Disabled' -and
    $t.Settings.Enabled -eq $false -and @(Children).Count -eq 0) 'NOT_QUIESCED'
}
function PolicyOld {
  $raw=ReadPolicy
  Need ($raw -ceq $originalPolicy) 'ORIGINAL_POLICY_MOVED'
}
function SourceOld {
  Need ((ReadSource $originalRoot) -ceq $old) 'ORIGINAL_SOURCE_MOVED'
}
function LedgerSource([string]$expected) {
  $program=@'
import sqlite3,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve()
con=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,isolation_level=None,timeout=10)
con.execute("PRAGMA query_only=ON")
assert con.execute("PRAGMA quick_check").fetchone()[0]=="ok"
m=con.execute("SELECT source_sha,enabled,legacy_suspended,head_seq,head_hash FROM meta WHERE id=1").fetchone()
assert m is not None and m[0]==sys.argv[2] and m[1]==1 and m[2]==1 and m[3]>=1826 and len(m[4])==64
print(str(m[3])+":"+str(m[4]))
con.close()
'@
  $lines=@($program | & $python -B - $database $expected)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
    $lines[0] -cmatch '^[0-9]+:[a-f0-9]{64}$') 'LEDGER_CUSTODY'
  return [string]$lines[0]
}
function Main {
  $sha=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha' |
    Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $sha -ceq $Target) 'PROTECTED_MAIN_MOVED'
}

# Fail without mutation unless exact original first-attempt issue event.
Need ($Target -cmatch '^[a-f0-9]{40}$' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'ORIGINAL_OWNER_EVENT'
Need ((ReadSource $env:GITHUB_WORKSPACE) -ceq $Target) 'WORKSPACE_NOT_TARGET'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  [string]$event.comment.body -clike 'F139-V41-LIVE-INSTALL *') 'EXACT_OWNER_COMMENT'
$id=[Security.Principal.WindowsIdentity]::GetCurrent()
$administrator=[Security.Principal.WindowsPrincipal]::new($id)
Need ($administrator.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'ADMIN_REQUIRED'
$data=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$stage=Join-Path $data ('release-candidates\'+$Target)
$binary=Join-Path $data ('genenv-source\'+$Target+'\f139-genenv-source.exe')
Need ((Test-Path -LiteralPath $stage -PathType Container) -and
  (Test-Path -LiteralPath $binary -PathType Leaf) -and
  (ReadSource $stage) -ceq $Target) 'STAGED_CANDIDATE_MISSING'
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
Need ([string]$task.State -cin @('Running','Ready') -and
  $task.Settings.Enabled -eq $true -and
  @($task.Actions).Count -eq 1 -and
  @($task.Triggers).Count -eq 3) 'EXISTING_OWNER_TASK_DRIFT'
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
  Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
Need ([string]$task.Principal.UserId -ieq $id.Name -or
  $sid -ceq $id.User.Value) 'ORIGINAL_SID_DRIFT'
$originalArgs=[string]$task.Actions[0].Arguments
$originalRoot=OwnerArg $task 'RepositoryRoot'
$database=OwnerArg $task 'Database'
$python=OwnerArg $task 'PythonExe'
$oldWrapper=OwnerArg $task 'File'
Need ([IO.Path]::GetFullPath($database) -ieq
  [IO.Path]::GetFullPath((Join-Path $data 'state.sqlite')) -and
  [IO.Path]::GetFileName($oldWrapper) -ceq 'Run-FORGE-F139.ps1' -and
  (Test-Path -LiteralPath $python -PathType Leaf) -and
  ($originalArgs -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)')) 'ORIGINAL_OWNER_ARGUMENTS'
SourceOld
$originalPolicy=ReadPolicy
$p=$originalPolicy|ConvertFrom-Json
Need ($p.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
  $p.enabled -eq $true -and $p.source_sha -ceq $old -and
  @($p.lanes).Count -eq 2 -and $p.lanes[0] -ceq 'Wingless' -and
  $p.lanes[1] -ceq 'Yggdrasil' -and
  $p.scientific_first_use -eq $false -and $p.paid_model_calls -eq 0 -and
  $p.new_controller -eq $false -and $p.new_scheduler -eq $false -and
  $p.new_queue -eq $false) 'POLICY_PRECOMMIT'
Main
$preimage=LedgerSource $old

# All owner-authentication and source-bound release checks are delegated to
# the same audited Python primitive used for the atomic original DB operation.
# A separate qualified activation and forward-repair phase must be present.
$env:PYTHONPATH=$stage
$env:F139_V41_INSTALL_WRAPPER='F139_V41_ACTIVATION_AND_FORWARD_REPAIR_QUALIFIED_V1'
$preflight=@'
import json,os,sys
from pathlib import Path
from f139.local_controller import GitHub
from f139.nci04_owner_issue import decode_unique
from f139.nci04_v41_native_original_commit import verify_install_dispatch
e=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes(),object_pairs_hook=decode_unique)
r=verify_install_dispatch(dict(os.environ),e,GitHub().native_repo_get)
assert r["target_source_sha"]==sys.argv[1]
from f139.nci04_native_contract import canonical
print("F139_V41_INSTALL_OWNER_INTENT_READBACK="+canonical(r).decode("ascii"))
'@
Push-Location $stage
try {
  $checked=@($preflight | & $python -B - $Target)
  Need ($LASTEXITCODE -eq 0 -and $checked.Count -eq 1 -and
    $checked[0] -cmatch '^F139_V41_INSTALL_OWNER_INTENT_READBACK=') 'OWNER_APPROVAL_EVENT_MISSING'
  $request=$checked[0].Substring('F139_V41_INSTALL_OWNER_INTENT_READBACK='.Length)|ConvertFrom-Json
  Need ($request.target_source_sha -ceq $Target -and
    [int64]$request.owner_approval_comment_id -gt 0) 'OWNER_INTENT_READBACK'
} finally {Pop-Location}
# Bind owner approval to the actual original task/SID and real CI artifact.
# The existing Python verifier independently double-reads the same comment.
$ownerApproval=@(& gh api ('repos/spoonman136668-ai/FORGE/issues/comments/'+
  [string]$request.owner_approval_comment_id))
Need ($LASTEXITCODE -eq 0 -and $ownerApproval.Count -ge 1) 'OWNER_APPROVAL_FETCH'
$comment=($ownerApproval -join [Environment]::NewLine)|ConvertFrom-Json
$prefix='F139-V41-OWNER-APPROVAL '
Need ($comment.id -eq $request.owner_approval_comment_id -and
  $comment.user.login -ceq 'spoonman136668-ai' -and
  $comment.author_association -ceq 'OWNER' -and
  $comment.issue_url -ceq 'https://api.github.com/repos/spoonman136668-ai/FORGE/issues/807' -and
  [string]$comment.body -clike ($prefix+'*')) 'OWNER_APPROVAL_IDENTITY'
$approval=([string]$comment.body).Substring($prefix.Length)|ConvertFrom-Json
$xml=Export-ScheduledTask -TaskName $name
$taskBytes=[Text.Encoding]::UTF8.GetBytes([string]$xml)
$taskSha=([BitConverter]::ToString(
  [Security.Cryptography.SHA256]::Create().ComputeHash($taskBytes))).
  Replace('-','').ToLowerInvariant()
$sidBytes=[Text.Encoding]::UTF8.GetBytes([string]$id.User.Value)
$sidSha=([BitConverter]::ToString(
  [Security.Cryptography.SHA256]::Create().ComputeHash($sidBytes))).
  Replace('-','').ToLowerInvariant()
Need ($approval.owner_comment_id -eq $request.owner_approval_comment_id -and
  $approval.from_source_sha -ceq $old -and
  $approval.to_source_sha -ceq $Target -and
  $approval.original_task_definition_sha256 -ceq $taskSha -and
  $approval.original_owner_sid_sha256 -ceq $sidSha) 'APPROVED_TASK_OR_SID_HASH_MISMATCH'
$runData=@(& gh api ('repos/spoonman136668-ai/FORGE/actions/runs/'+
  [string]$approval.qualification_run_id))
Need ($LASTEXITCODE -eq 0 -and $runData.Count -ge 1) 'QUALIFICATION_RUN_READ'
$run=($runData -join [Environment]::NewLine)|ConvertFrom-Json
Need ($run.id -eq $approval.qualification_run_id -and
  $run.head_sha -ceq $Target -and
  $run.head_branch -ceq 'main' -and
  $run.event -ceq 'push' -and
  $run.actor.login -ceq 'spoonman136668-ai' -and
  $run.run_attempt -eq 1 -and
  $run.status -ceq 'completed' -and $run.conclusion -ceq 'success' -and
  [string]$run.name -cin @('FORGE public Linux and Windows qualification',
                          'FORGE F73 protected-main cryptographic origin (no science permission)')) 'QUALIFICATION_RUN_SOURCE_DRIFT'
$artifactData=@(& gh api ('repos/spoonman136668-ai/FORGE/actions/artifacts/'+
  [string]$approval.qualification_artifact_id))
Need ($LASTEXITCODE -eq 0 -and $artifactData.Count -ge 1) 'QUALIFICATION_ARTIFACT_READ'
$artifact=($artifactData -join [Environment]::NewLine)|ConvertFrom-Json
Need ($artifact.id -eq $approval.qualification_artifact_id -and
  $artifact.expired -eq $false -and
  $artifact.workflow_run.id -eq $run.id -and
  [string]$artifact.digest -ceq ('sha256:'+$approval.qualification_artifact_sha256)) 'QUALIFICATION_ARTIFACT_DIGEST_DRIFT'
Write-Host 'F139_V41_AUTHENTIC_OWNER_TASK_SID_AND_CI_ARTIFACT=PASS'
# A failed preflight never changes task/policy/SQLite.
$lease=$null
try {
  Add-Type -Path (Join-Path $stage 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
  $lease=[F139OriginalOwnerMutex]::Acquire(
    [IO.Path]::ChangeExtension($database,'.lock'),120000)
  Need ((LedgerSource $old) -ceq $preimage) 'ORIGINAL_LEDGER_MOVED'
  Main
  PolicyOld
  SourceOld
  $disabled=$true
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $taskNow=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  if([string]$task.State -ceq 'Running'){
    Stop-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  }
  for($i=0;$i -lt 40;$i++){
    if(@(Children).Count -eq 0){break}
    Start-Sleep -Seconds 1
  }
  Disabled
  Need ((LedgerSource $old) -ceq $preimage) 'PRECOMMIT_LEDGER_CHANGED'
  $lease.Dispose();$lease=$null
  # Commit is the irreversible boundary. Never start V40 after this point.
  $commitEntered=$true
  Push-Location $stage
  try {
    $output=@(& $python -B -m f139.nci04_v41_native_original_install_cli --target $Target)
  } finally {Pop-Location}
  Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1 -and
    $output[0] -cmatch '^F139_V41_NATIVE_COMMIT_HOLD=') 'COMMIT_OR_POSTCOMMIT_HOLD'
  $receipt=$output[0].Substring('F139_V41_NATIVE_COMMIT_HOLD='.Length)|ConvertFrom-Json
  Need ($receipt.schema -ceq 'forge.f139.v41.native-commit-and-hold-cli.v1' -and
    $receipt.target_source_sha -ceq $Target -and
    $receipt.original_owner_task_still_disabled -eq $true -and
    $receipt.postcommit_hold_receipt.original_owner_task_disabled -eq $true -and
    $receipt.commit_receipt.original_sqlite_committed -eq $true -and
    $receipt.original_database_rollback_authorized -eq $false) 'POSTCOMMIT_ACCEPTANCE_HOLD'
  Disabled
  Need ((LedgerSource $Target) -cmatch '^[0-9]+:[a-f0-9]{64}$') 'POSTCOMMIT_DB_NOT_TARGET'
  Need ((ReadPolicy) -ceq $originalPolicy) 'OLD_POLICY_MOVED_EARLY'
  Main

  # Preserve all existing policy fields and mutate ONLY the source SHA.
  Need ($originalPolicy.Split(@($old),[StringSplitOptions]::None).Count -eq 2) 'OLD_SOURCE_NOT_UNIQUE'
  $updatedPolicy=$originalPolicy.Replace($old,$Target)
  & gh api --method PATCH repos/spoonman136668-ai/FORGE/issues/807 -f ('body='+$updatedPolicy) --silent
  Need ($LASTEXITCODE -eq 0) 'POLICY_PATCH_FAILED_HOLD'
  Need ((ReadPolicy) -ceq $updatedPolicy -and
    (ReadPolicy) -ceq $updatedPolicy) 'NEW_POLICY_READBACK_HOLD'
  Disabled

  # Replace BOTH exact old-root references; preserve executable, Python,
  # database, secret-file location, arguments, principal and three triggers.
  Need (($originalArgs.Split(@($originalRoot),[StringSplitOptions]::None).Count -eq 3) -and
    (Test-Path -LiteralPath (Join-Path $stage 'scripts/Run-FORGE-F139.ps1') -PathType Leaf)) 'OLD_TASK_ROOT_NOT_EXACT'
  $newArgs=$originalArgs.Replace($originalRoot,$stage)
  $oldAction=$task.Actions[0]
  $workingDir=[string]$oldAction.WorkingDirectory
  if($workingDir -ceq $originalRoot){$workingDir=$stage}
  if($workingDir){
    $newAction=New-ScheduledTaskAction -Execute ([string]$oldAction.Execute) -Argument $newArgs -WorkingDirectory $workingDir
  } else {
    $newAction=New-ScheduledTaskAction -Execute ([string]$oldAction.Execute) -Argument $newArgs
  }
  Set-ScheduledTask -TaskName $name -Action $newAction -ErrorAction Stop|Out-Null
  $retargeted=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ($retargeted.Settings.Enabled -eq $false -and
    [string]$retargeted.State -ceq 'Disabled' -and
    @($retargeted.Actions).Count -eq 1 -and
    @($retargeted.Triggers).Count -eq 3 -and
    [string]$retargeted.Actions[0].Arguments -ceq $newArgs -and
    [string]$retargeted.Principal.UserId -ceq [string]$task.Principal.UserId) 'TASK_RETARGET_READBACK_HOLD'
  Need ((ReadPolicy) -ceq $updatedPolicy -and
    (LedgerSource $Target) -cmatch '^[0-9]+:[a-f0-9]{64}$') 'PREACTIVATION_STATE_MOVED'
  Main

  # Same original task, no new scheduler or controller.
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $live=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ($live.Settings.Enabled -eq $true -and
    [string]$live.State -cin @('Ready','Running') -and
    [string]$live.Actions[0].Arguments -ceq $newArgs -and
    (ReadPolicy) -ceq $updatedPolicy -and
    (LedgerSource $Target) -cmatch '^[0-9]+:[a-f0-9]{64}$') 'LIVE_TASK_OR_DB_READBACK'
  # Full behavioral/scientific acceptance is independent of successful start.
  $activated=$true
  Write-Host ('F139_V41_NATIVE_INSTALL_RECEIPT='+($receipt|ConvertTo-Json -Depth 16 -Compress))
  Write-Host 'F139_V41_SAME_ORIGINAL_TASK_ACTIVATED=PASS'
  Write-Host 'F139_V41_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Host 'F139_V41_HYBRID_ADMISSION=FALSE'
} catch {
  $reason=$_.Exception.Message
  if($lease){$lease.Dispose();$lease=$null}
  if($disabled -and -not $commitEntered) {
    # Only a verified untouched original can be resumed before commit entry.
    try {
      Disabled
      SourceOld
      PolicyOld
      Need ((LedgerSource $old) -ceq $preimage) 'V40_RECOVERY_LEDGER_CHANGED'
      Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Write-Warning 'F139_V41_PRECOMMIT_V40_SAFELY_RESUMED'
    } catch {
      Write-Warning 'F139_V41_PRECOMMIT_RECOVERY_UNVERIFIED_HOLD'
    }
  } elseif($commitEntered -and -not $activated) {
    # Never restore an older SQLite or resume V40 after an uncertain commit.
    try {
      Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    } catch {}
    Write-Warning 'F139_V41_POSTCOMMIT_FORWARD_REPAIR_ONLY_ORIGINAL_DB_UNTOUCHED'
  }
  throw ('F139_V41_LIVE_INSTALL_NOT_ACCEPTED: '+$reason)
} finally {
  if($lease){$lease.Dispose();$lease=$null}
}
