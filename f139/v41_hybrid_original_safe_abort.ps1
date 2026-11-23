# Original V41 PAUSE-HOLD abort: one separately OWNER-approved same-task restart.
# NOT connected to any workflow, schedule or automatic dispatch. NO retry.
# Only if authentic V41 source was NEVER committed and FULL current SQLite
# matches a sealed detached cold backup; otherwise FAIL CLOSED and keep hold.
param([Parameter(Mandatory=$true)][string]$Target)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskName='FORGE-F139-UnifiedController'
$old='1a40fe4e3ec6e93a1631d59863b95e90981d734e'
$lease=$null
$startAttempted=$false
function Need([bool]$ok,[string]$code) {
  if(-not $ok){throw ('F139_HYBRID_V41_ABORT_'+$code)}
}
function Arg($task,[string]$name) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  Need $m.Success 'ORIGINAL_TASK_ARGUMENT_MISSING'
  return $m.Groups[1].Value
}
function Task {
  $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try{
    $sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
      Translate([Security.Principal.SecurityIdentifier]).Value
  }catch {}
  Need (@($task.Actions).Count -eq 1 -and
    @($task.Triggers).Count -eq 3 -and
    [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe' -and
    ([string]$task.Principal.UserId -ieq $identity.Name -or
      $sid -ceq $identity.User.Value)) 'ORIGINAL_OWNER_SID_OR_TASK_TOPOLOGY'
  Need ([IO.Path]::GetFileName((Arg $task 'File')) -ceq
    'Run-FORGE-F139.ps1') 'ORIGINAL_TASK_WRAPPER_DRIFT'
  return $task
}
function Disabled([string]$database) {
  $t=Task
  Need ([string]$t.State -ceq 'Disabled' -and $t.Settings.Enabled -eq $false) 'TASK_NOT_DISABLED'
  $running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop|
    Where-Object {$_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
  Need ($running.Count -eq 0) 'ORIGINAL_CONTROLLER_CHILD_STILL_RUNNING'
}
function Source {
  $main=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha' | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $main -ceq $Target) 'PROTECTED_MAIN_MOVED'
}
function Policy {
  $body=(& gh api repos/spoonman136668-ai/FORGE/issues/807 --jq '.body' | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $body.Length -gt 0) 'OWNER_POLICY_READ_FAILED'
  $p=$body|ConvertFrom-Json
  Need ($p.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
    $p.source_sha -ceq $old -and $p.enabled -eq $true -and
    @($p.lanes).Count -eq 2 -and
    $p.lanes[0] -ceq 'Wingless' -and $p.lanes[1] -ceq 'Yggdrasil' -and
    $p.scientific_first_use -eq $false -and $p.paid_model_calls -eq 0 -and
    $p.new_controller -eq $false -and $p.new_scheduler -eq $false -and
    $p.new_queue -eq $false) 'ORIGINAL_OWNER_POLICY_CHANGED'
  return $body
}
function Checkouts([string]$oldRoot) {
  $candidate=(& git -C $env:GITHUB_WORKSPACE rev-parse HEAD|Out-String).Trim()
  $dirty=@(& git -C $env:GITHUB_WORKSPACE status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $candidate -ceq $Target -and
    $dirty.Count -eq 0) 'CANDIDATE_CHECKOUT_NOT_EXACT_OR_CLEAN'
  $installed=(& git -C $oldRoot rev-parse HEAD|Out-String).Trim()
  $installedDirty=@(& git -C $oldRoot status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $installed -ceq $old -and
    $installedDirty.Count -eq 0) 'ORIGINAL_V41_CHECKOUT_CHANGED'
}

Need ($Target -cmatch '^[a-f0-9]{40}$' -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'ORIGINAL_WIN_OWNER_FIRST_ATTEMPT_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_EVENT_PATH -PathType Leaf) 'ORIGINAL_ABORT_EVENT_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_WORKSPACE -PathType Container) 'MERGED_SOURCE_REQUIRED'
$e=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
Need ($e.action -ceq 'created' -and $e.issue.number -eq 807 -and
  $null -eq $e.issue.PSObject.Properties['pull_request'] -and
  $e.sender.login -ceq 'spoonman136668-ai' -and
  $e.comment.user.login -ceq 'spoonman136668-ai' -and
  $e.comment.author_association -ceq 'OWNER' -and
  [string]$e.comment.body -cmatch ('^F139-HYBRID-V41-SAFE-ABORT '+$Target+' ')) 'EXPLICIT_SEPARATE_SAFE_ABORT_COMMENT_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($identity)
Need ($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_OWNER_ADMIN_REQUIRED'
$t=Task
$db=Arg $t 'Database'
$root=Arg $t 'RepositoryRoot'
$python=Arg $t 'PythonExe'
Need ([IO.Path]::GetFullPath($db) -ieq
  [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite')) -and
  (Test-Path -LiteralPath $db -PathType Leaf) -and
  (Test-Path -LiteralPath $root -PathType Container) -and
  (Test-Path -LiteralPath $python -PathType Leaf)) 'ORIGINAL_OWNER_FILE_IDENTITY_DRIFT'
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
Disabled $db
Checkouts $root
Source
$policyBefore=Policy
# Read-only complete 1829+ event replay, all-table digest and detached restore.
$output=@(& $python -B -m f139.nci04_v41_hybrid_safe_abort --target $Target)
Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1 -and
  $output[0].StartsWith('F139_HYBRID_V41_SAFE_ABORT_PREFLIGHT=',
    [StringComparison]::Ordinal)) 'AUTHENTIC_ORIGINAL_ABORT_PREFLIGHT_REQUIRED'
$proof=$output[0].Substring('F139_HYBRID_V41_SAFE_ABORT_PREFLIGHT='.Length)|ConvertFrom-Json
Need ($proof.schema -ceq 'forge.f139.hybrid-v41.original-safe-abort-preflight.v1' -and
  $proof.target_source_sha -ceq $Target -and
  $proof.original_source_sha -ceq $old -and
  $proof.frozen_precommit_unchanged -eq $true -and
  $proof.complete_detached_restore_verified -eq $true -and
  $proof.eligible_for_separately_approved_same_original_task_abort -eq $true -and
  $proof.original_owner_mutations -eq 0 -and
  $proof.source_transition_authorized -eq $false -and
  $proof.hybrid_admission -eq $false -and
  $proof.scientific_first_use -eq $false -and
  $proof.logical_all_tables_sha256 -cmatch '^[a-f0-9]{64}$') 'SAFE_ABORT_RECEIPT_NOT_QUALIFIED'
# Native owner mutex prevents an intervening original-controller or source
# commit after preflight; under it we rehash the WHOLE read-only SQLite.
Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
try {
  $lease=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($db,'.lock'),120000)
  Disabled $db
  Checkouts $root
  Source
  Need ((Policy) -ceq $policyBefore) 'POLICY_MOVED_BEFORE_RESUME'
  $code=@'
import sqlite3,sys
from pathlib import Path
from f139.nci04_native_contract import canonical,digest
from f139.nci04_v41_hybrid_cold_bundle import rollback_view
p=Path(sys.argv[1]).resolve()
db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,isolation_level=None,timeout=10)
db.row_factory=sqlite3.Row
db.execute("PRAGMA query_only=ON")
assert db.execute("PRAGMA quick_check").fetchone()[0]=="ok"
m=db.execute("SELECT source_sha,enabled,legacy_suspended,head_seq,head_hash FROM meta WHERE id=1").fetchone()
assert m["source_sha"]==sys.argv[2] and m["enabled"]==1 and m["legacy_suspended"]==1
assert m["head_seq"]==int(sys.argv[3]) and m["head_hash"]==sys.argv[4]
assert db.execute("SELECT COUNT(*) FROM events WHERE seq>?",(m["head_seq"],)).fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM tasks WHERE stage IN ('READY','ACTIVE')").fetchone()[0]==0
assert digest(canonical(rollback_view(db)))==sys.argv[5]
assert db.total_changes==0
db.close()
print("F139_HYBRID_V41_SAFE_ABORT_LOCKED_FULL_SQLITE=PASS")
'@
  $readback=@($code|& $python -B - $db $old ([string]$proof.original_head_seq) ([string]$proof.original_head_sha256) ([string]$proof.logical_all_tables_sha256))
  Need ($LASTEXITCODE -eq 0 -and $readback.Count -eq 1 -and
    $readback[0] -ceq 'F139_HYBRID_V41_SAFE_ABORT_LOCKED_FULL_SQLITE=PASS') 'FINAL_LOCKED_ORIGINAL_DATABASE_CHANGED'
  Disabled $db
  Checkouts $root
  Source
  Need ((Policy) -ceq $policyBefore) 'FINAL_POLICY_DRIFT'
  # Exactly one attempt to enable and start the EXISTING ORIGINAL task.
  # Do not restore a database; NEVER retry after uncertain effects.
  Enable-ScheduledTask -TaskName $taskName -ErrorAction Stop|Out-Null
  $startAttempted=$true
  Start-ScheduledTask -TaskName $taskName -ErrorAction Stop|Out-Null
  $final=Task
  Need ($final.Settings.Enabled -eq $true -and
    [string]$final.State -cin @('Ready','Running')) 'POST_ABORT_SAME_TASK_START_UNVERIFIED'
  Need ((Policy) -ceq $policyBefore) 'POST_ABORT_ORIGINAL_POLICY_DRIFT'
  Write-Host 'F139_HYBRID_V41_SAFE_ABORT_SAME_ORIGINAL_TASK=PASS'
  Write-Host 'F139_HYBRID_V41_SAFE_ABORT_SOURCE_TRANSITION=FALSE'
  Write-Host 'F139_HYBRID_V41_SAFE_ABORT_HYBRID_ADMISSION=FALSE'
  Write-Host 'F139_HYBRID_V41_SAFE_ABORT_SCIENTIFIC_FIRST_USE=FALSE'
} catch {
  if($startAttempted){
    throw ('F139_HYBRID_V41_ABORT_START_UNCERTAIN_NO_RETRY: '+$_.Exception.Message)
  }
  throw ('F139_HYBRID_V41_ABORT_FAILED_KEEP_HOLD_NO_RETRY: '+$_.Exception.Message)
} finally {
  if($lease){$lease.Dispose();$lease=$null}
}
