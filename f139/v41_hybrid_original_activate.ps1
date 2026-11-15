# Existing ORIGINAL owner only. Complete an already committed V41->Hybrid
# source HOLD: migrate the same SQLite lane, update only issue 807 source/lanes,
# retarget and restart the SAME task. No new controller, runner, queue, science.
# Separately triggered by a new OWNER SOURCE-ACTIVATE comment, never auto-retry.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$name='FORGE-F139-UnifiedController'
$old='1a40fe4e3ec6e93a1631d59863b95e90981d734e'
$taskEnabled=$false
$taskStartAttempted=$false
function Need([bool]$ok,[string]$why) {
  if(-not $ok){throw ('F139_HYBRID_V41_ACTIVATE_'+$why)}
}
function OriginalTask {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try {
    $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
      Translate([Security.Principal.SecurityIdentifier]).Value
  }catch {}
  Need (@($t.Actions).Count -eq 1 -and @($t.Triggers).Count -eq 3 -and
    [IO.Path]::GetFileName([string]$t.Actions[0].Execute) -ieq 'powershell.exe' -and
    ([string]$t.Principal.UserId -ieq $who.Name -or
      $sid -ceq $who.User.Value)) 'ORIGINAL_TASK_IDENTITY_CHANGED'
  return $t
}
function Arg($t,[string]$key) {
  $m=[regex]::Match([string]$t.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success ('ORIGINAL_ARGUMENT_'+$key)
  return [string]$m.Groups[1].Value
}
function Main {
  $remote=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha'|Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $remote -ceq $Target) 'PROTECTED_MAIN_MOVED'
}
function Source([string]$folder,[string]$sha) {
  Need (Test-Path -LiteralPath $folder -PathType Container) 'SOURCE_MISSING'
  $now=(& git -C $folder rev-parse HEAD|Out-String).Trim()
  $dirty=@(& git -C $folder status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $now -ceq $sha -and
    $dirty.Count -eq 0) 'SOURCE_NOT_EXACT_AND_CLEAN'
}
function Policy {
  $doc=(& gh api repos/spoonman136668-ai/FORGE/issues/807 --jq '.body'|Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $doc.Length -gt 0) 'POLICY_READ_FAILED'
  return $doc
}
function Children {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($db)})
}
function Disabled {
  $t=OriginalTask
  Need ([string]$t.State -ceq 'Disabled' -and
    $t.Settings.Enabled -eq $false -and
    @(Children).Count -eq 0) 'ORIGINAL_TASK_NOT_QUIESCED'
  return $t
}

Need ($Target -cmatch '^[a-f0-9]{40}$' -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  -not $env:OPENAI_API_KEY) 'ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_EVENT_PATH -PathType Leaf) 'OWNER_EVENT_REQUIRED'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [string]$event.comment.body -cmatch
   ('^F139-HYBRID-V41-SOURCE-ACTIVATE '+$Target+' [1-9][0-9]*$')) 'DISTINCT_OWNER_ACTIVATION_EVENT_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'OWNER_ADMIN_REQUIRED'
$t=Disabled
$db=Arg $t 'Database'
$root=Arg $t 'RepositoryRoot'
$python=Arg $t 'PythonExe'
$wrapper=Arg $t 'File'
Need ([IO.Path]::GetFullPath($db) -ieq
  [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite')) -and
  [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
  (Test-Path -LiteralPath $db -PathType Leaf) -and
  (Test-Path -LiteralPath $python -PathType Leaf)) 'EXACT_ORIGINAL_TASK_FILES_REQUIRED'
$stage=Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$Target)
Source $env:GITHUB_WORKSPACE $Target
# The failed V41 activation may have retargeted the DISABLED task.
# Admit only the two immutable historic checkouts already validated by
# nci04_v41_hybrid_forward_owner_profile. Do not infer arbitrary roots.
$heldSource=(& git -C $root rev-parse HEAD|Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $heldSource -cin @(
  '2c7caad5a4502d4b874a11d57207a35cf033eb08',
  'c611c4362e3cc867984448a03ecdf3be923d2ef1')) 'ORIGINAL_HELD_SOURCE_NOT_AUTHENTIC'
Source $root $heldSource
Source $stage $Target
Main
$oldPolicy=Policy
$p=$oldPolicy|ConvertFrom-Json
Need ($p.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
  $p.enabled -eq $true -and $p.source_sha -ceq $old -and
  @($p.lanes).Count -eq 2 -and
  $p.lanes[0] -ceq 'Wingless' -and $p.lanes[1] -ceq 'Yggdrasil' -and
  $p.max_issue_creations_per_cycle -eq 2 -and
  $p.require_owner_authored_pr -eq $true -and
  $p.require_single_head_commit_delta -eq $true -and
  $p.require_single_allowed_source_file -eq $true -and
  $p.scientific_first_use -eq $false -and
  $p.new_controller -eq $false -and
  $p.new_scheduler -eq $false -and
  $p.new_queue -eq $false -and
  $p.paid_model_calls -eq 0 -and
  $p.accepted_ref_mutations -eq 0) 'ORIGINAL_TWO_LANE_POLICY_DRIFT'

# Authenticate the distinct owner activation comment and its preceding
# SOURCE-COMMIT chain; cold-replay the original 153 verified/56 quarantined
# tasks under the EXISTING owner mutex, without rewriting a single byte.
$program=@'
import json,os,re,sys
from pathlib import Path
from f139.local_controller import GitHub
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_forward_postcommit as postcommit
from f139 import nci04_v41_hybrid_forward_readiness as readiness

e=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text("utf-8"),
             object_pairs_hook=decode_unique)
target=sys.argv[1]
db=Path(sys.argv[2])
api=GitHub()
get=api.native_repo_get
body=e["comment"]["body"]
m=re.fullmatch(r"F139-HYBRID-V41-SOURCE-ACTIVATE "+
               re.escape(target)+r" ([1-9][0-9]*)",body)
assert m is not None
postcommit_id=int(m.group(1))
current_id=e["comment"]["id"]
assert type(current_id) is int and postcommit_id<current_id
assert readiness._owner_comment(get,current_id,body)==e["comment"]["created_at"]
prior=get("repos/"+readiness.REPO+"/issues/comments/"+str(postcommit_id))
assert type(prior) is dict and prior.get("id")==postcommit_id
assert type(prior.get("body")) is str
assert prior["body"].startswith(postcommit.PREFIX+target+" ")
assert readiness._owner_comment(get,postcommit_id,prior["body"])<e["comment"]["created_at"]
# The forward-postcommit verifier reauthenticates the actual source intent,
# detached cold bundle, immutable event 1831, task/SID/lease and 153/56 history.
# This is read-only. Migration remains a separate owner-only operation below.
previous={"action":"created","issue":e["issue"],"sender":e["sender"],
          "comment":prior}
receipt=postcommit.original_postcommit(db,dict(os.environ),previous,api)
assert receipt["schema"]==postcommit.RECEIPT
assert receipt["source_sha"]==target and receipt["event_seq"]==1831
assert receipt["verified_historical_tasks"]==153
assert receipt["custodied_negative_tasks"]==56
assert receipt["original_owner_mutations"]==0
assert receipt["hybrid_schema_migrated"] is False
assert receipt["scientific_first_use"] is False
assert receipt["task_resume_authorized"] is False
print("F139_HYBRID_V38_EVENT1831_ACTIVATION_PREFLIGHT="+
      canonical(dict(schema="forge.f139.hybrid-v38.activation-preflight.v1",
       source_sha=target,source_event_seq=receipt["event_seq"],
       source_event_head_sha256=receipt["event_head_sha256"],
       postcommit_comment_id=postcommit_id,
       activation_comment_id=current_id,
       verified_historical_tasks=153,custodied_negative_tasks=56,
       original_owner_mutations=0,source_committed_once=True,
       cold_recovery_verified=True,hybrid_science_first_use=False)).decode("ascii"))
'@
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
$pre=@($program|& $python -B - $Target $db)
Need ($LASTEXITCODE -eq 0 -and $pre.Count -eq 1 -and
  $pre[0].StartsWith('F139_HYBRID_V38_EVENT1831_ACTIVATION_PREFLIGHT=',
    [StringComparison]::Ordinal)) 'AUTHENTIC_HELD_SOURCE_READBACK_REQUIRED'
$proof=$pre[0].Substring('F139_HYBRID_V38_EVENT1831_ACTIVATION_PREFLIGHT='.Length)|ConvertFrom-Json
Need ($proof.schema -ceq 'forge.f139.hybrid-v38.activation-preflight.v1' -and
  $proof.source_sha -ceq $Target -and
  $proof.source_event_seq -eq 1831 -and
  $proof.verified_historical_tasks -eq 153 -and
  $proof.custodied_negative_tasks -eq 56 -and
  $proof.original_owner_mutations -eq 0 -and
  $proof.cold_recovery_verified -eq $true -and
  $proof.source_committed_once -eq $true -and
  $proof.hybrid_science_first_use -eq $false) 'COLD_OR_COMMENT_PROOF_DRIFT'

# The existing owner task is the ONLY task we touch. Keep disabled while
# retargeting, migrating its existing SQLite and updating the same policy.
$oldArgs=[string]$t.Actions[0].Arguments
Need (($oldArgs.Split(@($root),[StringSplitOptions]::None).Count -eq 3) -and
  (Test-Path -LiteralPath (Join-Path $stage 'scripts/Run-FORGE-F139.ps1') -PathType Leaf)) 'ORIGINAL_ACTION_NOT_SINGLE_REPLACEABLE'
$newArgs=$oldArgs.Replace($root,$stage)
$action=$t.Actions[0]
$work=[string]$action.WorkingDirectory
if($work -ceq $root){$work=$stage}
$newAction=if($work) {
  New-ScheduledTaskAction -Execute ([string]$action.Execute) -Argument $newArgs -WorkingDirectory $work
} else {
  New-ScheduledTaskAction -Execute ([string]$action.Execute) -Argument $newArgs
}
try {
  Main
  Need ((Policy) -ceq $oldPolicy) 'PRETARGET_POLICY_CHANGED'
  $null=Disabled
  Set-ScheduledTask -TaskName $name -Action $newAction -ErrorAction Stop|Out-Null
  $retargeted=Disabled
  Need ([string]$retargeted.Actions[0].Arguments -ceq $newArgs -and
    [string]$retargeted.Principal.UserId -ceq [string]$t.Principal.UserId -and
    @($retargeted.Triggers).Count -eq 3) 'TARGET_TASK_NOT_ORIGINAL'
  # Existing owner CLI performs a one-time, cold-audited atomic schema
  # migration and appends a single owner event; no Hybrid science permission.
  Source $stage $Target
  Main
  $env:PYTHONPATH=$stage
  Push-Location $stage
  try {
    $migration=@(& $python -B -m f139.local_controller --db $db upgrade-hybrid-lane)
  } finally {Pop-Location}
  Need ($LASTEXITCODE -eq 0 -and $migration.Count -eq 1) 'HYBRID_LANE_MIGRATION_NOT_QUALIFIED'
  $migrated=$migration[0]|ConvertFrom-Json
  Need ($migrated.hybrid_development_lane_schema_admitted -eq $true -and
    $migrated.source_sha -ceq $Target -and
    $migrated.hybrid_model_training_started -eq $false -and
    $migrated.scientific_first_use -eq $false) 'MIGRATION_RECEIPT_INVALID'
  $null=Disabled
  Main
  Need ((Policy) -ceq $oldPolicy) 'POLICY_CHANGED_BEFORE_COMMIT'
  $p.source_sha=$Target
  $p.lanes=@('Wingless','Yggdrasil','TTT-Hybrid')
  $newPolicy=$p|ConvertTo-Json -Depth 8 -Compress
  # Update the EXISTING policy issue only; all non-source/lane fields are
  # unchanged. No new issue, scheduler, owner or control plane.
  & gh api --method PATCH repos/spoonman136668-ai/FORGE/issues/807 -f ('body='+$newPolicy) --silent
  Need ($LASTEXITCODE -eq 0) 'OWNER_POLICY_PATCH_NOT_VERIFIED'
  Need ((Policy) -ceq $newPolicy -and
    (Policy) -ceq $newPolicy) 'THREE_LANE_POLICY_READBACK_FAILED'
  $null=Disabled
  Source $stage $Target
  Main
  # This is the ONLY start of the existing task. No retry on uncertain effects.
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $taskEnabled=$true
  $taskStartAttempted=$true
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $live=OriginalTask
  Need ($live.Settings.Enabled -eq $true -and
    [string]$live.State -cin @('Running','Ready') -and
    [string]$live.Actions[0].Arguments -ceq $newArgs -and
    (Policy) -ceq $newPolicy) 'ORIGINAL_TASK_DID_NOT_RESUME'
  # A scheduler command returning success is NOT proof that the controller
  # actually resumed. Witness one active native controller process and cold
  # replay the same original SQLite with all three lanes intact.
  $children=@()
  for($i=0;$i -lt 25;$i++){
    $children=@(Children)
    if($children.Count -eq 1){break}
    Start-Sleep -Seconds 1
  }
  Need ($children.Count -eq 1) 'ORIGINAL_CONTROLLER_PROCESS_NOT_RUNNING'
  $statusCode=@'
import json,sys
from contextlib import closing
from pathlib import Path
from f139.local_controller import Database
from f139.hybrid_owner_admission import is_migrated
with closing(Database.open_readonly(Path(sys.argv[1]))) as db:
    db.verify()
    meta=db.meta()
    assert meta["source_sha"]==sys.argv[2] and meta["enabled"]==1
    assert meta["legacy_suspended"]==1
    assert is_migrated(db)
    assert db.dual_native_schema()
    assert db.conn.execute("PRAGMA query_only").fetchone()[0]==1
    assert db.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]>=153
    assert db.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]==56
    assert db.conn.total_changes==0
print("F139_HYBRID_V41_THREE_LANE_COLD_READBACK=PASS")
'@
  $env:PYTHONPATH=$stage
  $status=@($statusCode|& $python -B - $db $Target)
  Need ($LASTEXITCODE -eq 0 -and $status.Count -eq 1 -and
    $status[0] -ceq 'F139_HYBRID_V41_THREE_LANE_COLD_READBACK=PASS') 'ORIGINAL_LEDGER_NOT_COLD_QUALIFIED'
  Need ((Policy) -ceq $newPolicy -and (Main) -eq $null) 'FINAL_SOURCE_POLICY_DRIFT'
  Write-Host 'F139_HYBRID_V41_ORIGINAL_CONTROLLER_PROCESS=PASS'
  Write-Host 'F139_HYBRID_V41_THREE_LANE_COLD_READBACK=PASS'
  Write-Host 'F139_HYBRID_V41_SAME_ORIGINAL_TASK_RESTART=PASS'
  Write-Host 'F139_HYBRID_V41_THREE_LANE_POLICY=PASS'
  Write-Host 'F139_HYBRID_V41_LANE_SCHEMA_MIGRATION=PASS'
  Write-Host 'F139_HYBRID_V41_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Host 'F139_HYBRID_V41_NEW_CONTROLLER=FALSE'
} catch {
  $reason=$_.Exception.Message
  # Source commit is already durable. NEVER reinstall V41 or restore its
  # earlier SQLite. If start effect is uncertain, do not call Start again.
  try {
    if($taskEnabled){
      Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    }
  }catch {}
  throw ('F139_HYBRID_V41_FORWARD_REPAIR_HOLD_NO_REPLAY: '+$reason)
}
