# Source-only V41 -> Hybrid original-task backup maintenance.
# NOT connected to GitHub Actions or automatically invoked.
# Two distinct original-owner issue comments are mandatory. No release.
param([Parameter(Mandatory=$true)][string]$Target)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$original='1a40fe4e3ec6e93a1631d59863b95e90981d734e'
$name='FORGE-F139-UnifiedController'
$paused=$false
$resumed=$false
$startAttempted=$false
$backupChildCleared=$true
$lease=$null
$before=$null
$policyBefore=$null
$db=$null
$root=$null
$python=$null

function Need([bool]$ok,[string]$reason) {
  if(-not $ok){throw ('F139_HYBRID_V41_MAINTENANCE_'+$reason)}
}
function TaskArg($task,[string]$key) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success 'TASK_ARGUMENT_INVALID'
  return $m.Groups[1].Value
}
function Task() {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try{
    $sid=(New-Object Security.Principal.NTAccount(
      [string]$t.Principal.UserId)).Translate(
      [Security.Principal.SecurityIdentifier]).Value
  } catch {}
  Need (@($t.Actions).Count -eq 1 -and @($t.Triggers).Count -eq 3 -and
    [IO.Path]::GetFileName([string]$t.Actions[0].Execute) -ieq 'powershell.exe' -and
    ([string]$t.Principal.UserId -ieq $who.Name -or
      $sid -ceq $who.User.Value)) 'ORIGINAL_TASK_SID_OR_TOPOLOGY_DRIFT'
  return $t
}
function Main() {
  $current=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha'|Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $current -ceq $Target) 'PROTECTED_MERGED_MAIN_MOVED'
}
function Policy() {
  $output=& gh api repos/spoonman136668-ai/FORGE/issues/807 --jq '.body'
  Need ($LASTEXITCODE -eq 0) 'OWNER_POLICY_READ_FAILED'
  $body=($output|Out-String).Trim()
  $doc=$body|ConvertFrom-Json
  Need ($doc.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
    $doc.enabled -eq $true -and $doc.source_sha -ceq $original -and
    @($doc.lanes).Count -eq 2 -and $doc.lanes[0] -ceq 'Wingless' -and
    $doc.lanes[1] -ceq 'Yggdrasil' -and
    $doc.scientific_first_use -eq $false -and
    $doc.new_controller -eq $false -and $doc.new_scheduler -eq $false -and
    $doc.new_queue -eq $false -and $doc.paid_model_calls -eq 0) 'OWNER_POLICY_DRIFT'
  return $body
}
function Checkouts() {
  $rev=(& git -C $env:GITHUB_WORKSPACE rev-parse HEAD|Out-String).Trim()
  $dirty=@(& git -C $env:GITHUB_WORKSPACE status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $rev -ceq $Target -and $dirty.Count -eq 0) 'CANDIDATE_SOURCE_DRIFT'
  $old=(& git -C $root rev-parse HEAD|Out-String).Trim()
  $oldDirty=@(& git -C $root status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $old -ceq $original -and
    $oldDirty.Count -eq 0) 'INSTALLED_V41_SOURCE_DRIFT'
}
function Children() {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($db)})
}
function Disabled() {
  $t=Task
  Need ([string]$t.State -ceq 'Disabled' -and
    $t.Settings.Enabled -eq $false -and
    @(Children).Count -eq 0) 'ORIGINAL_TASK_NOT_QUIESCED'
}
function Ledger() {
  $code=@'
import json,sqlite3,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve()
db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,isolation_level=None,timeout=10)
db.row_factory=sqlite3.Row
db.execute("PRAGMA query_only=ON")
assert db.execute("PRAGMA quick_check").fetchone()[0]=="ok"
m=dict(db.execute("SELECT source_sha,enabled,legacy_suspended,head_seq,head_hash FROM meta WHERE id=1").fetchone())
assert m["source_sha"]==sys.argv[2] and m["enabled"]==1 and m["legacy_suspended"]==1
assert type(m["head_seq"]) is int and m["head_seq"]>=1829 and len(m["head_hash"])==64
print(json.dumps(m,sort_keys=True,separators=(",",":")))
db.close()
'@
  $lines=@($code|& $python -B - $db $original)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1) 'ORIGINAL_LEDGER_UNVERIFIED'
  return ($lines[0]|ConvertFrom-Json)
}
function Unchanged() {
  $now=Ledger
  Need ($null -ne $before -and $now.source_sha -ceq $before.source_sha -and
    $now.head_seq -eq $before.head_seq -and
    $now.head_hash -ceq $before.head_hash) 'LEDGER_MUTATED_WHILE_PAUSED'
}
function Invoke-Pair([bool]$preflight,[int]$limitMs) {
  # Exactly one subprocess, bounded, with no hidden retries or stdout secrets.
  $proc=[System.Diagnostics.Process]::new()
  $proc.StartInfo.FileName=$python
  $proc.StartInfo.WorkingDirectory=$env:GITHUB_WORKSPACE
  $proc.StartInfo.UseShellExecute=$false
  $proc.StartInfo.RedirectStandardOutput=$true
  $proc.StartInfo.RedirectStandardError=$true
  $args=@('-B','-m','f139.nci04_v41_hybrid_pair_owner',
          '--db',$db,'--target',$Target)
  if($preflight){$args+=('--preflight-only')}
  foreach($arg in $args){[void]$proc.StartInfo.ArgumentList.Add([string]$arg)}
  Need ($proc.Start()) 'CANDIDATE_CHILD_START_DENIED'
  $script:backupChildCleared=$false
  $stdoutTask=$proc.StandardOutput.ReadToEndAsync()
  $stderrTask=$proc.StandardError.ReadToEndAsync()
  if(-not $proc.WaitForExit($limitMs)){
    $proc.Kill($true)
    Need ($proc.WaitForExit(30000)) 'CANDIDATE_CHILD_UNCERTAIN_EFFECT'
    $script:backupChildCleared=$true
    throw 'F139_HYBRID_V41_MAINTENANCE_CANDIDATE_CHILD_TIMEOUT'
  }
  $script:backupChildCleared=$true
  $stdout=$stdoutTask.GetAwaiter().GetResult()
  $null=$stderrTask.GetAwaiter().GetResult()
  Need ($proc.ExitCode -eq 0) 'PAIRED_OWNER_CUSTODY_OR_BACKUP_FAILED'
  $lines=@($stdout -split "\r?\n"|Where-Object {$_ -ne ''})
  Need ($lines.Count -eq 1) 'CANDIDATE_RECEIPT_NOT_UNIQUE'
  $prefix='F139_HYBRID_V41_PAIRED_BACKUP_ONLY='
  if($preflight){$prefix='F139_HYBRID_V41_PAIRED_PREFLIGHT='}
  Need ($lines[0].StartsWith($prefix,[StringComparison]::Ordinal)) 'RECEIPT_PREFIX_INVALID'
  return ($lines[0].Substring($prefix.Length)|ConvertFrom-Json)
}

Need ($Target -cmatch '^[a-f0-9]{40}$' -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'UNAUTHORIZED_RUNNER_OR_EVENT'

$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [string]$event.comment.body -cmatch ('^F139-HYBRID-V41-PAUSE-RESUME '+$Target+' [1-9][0-9]*$')) 'SEPARATE_APPROVAL_EVENT_REQUIRED'

$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($identity)
Need ($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_REQUIRED'
$t=Task
Need ([string]$t.State -cin @('Ready','Running') -and
  $t.Settings.Enabled -eq $true) 'OWNER_NOT_RUNNING'
$root=TaskArg $t 'RepositoryRoot'
$db=TaskArg $t 'Database'
$python=TaskArg $t 'PythonExe'
Need ([IO.Path]::GetFullPath($db) -ieq
  (Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite') -and
  (Test-Path -LiteralPath $python -PathType Leaf) -and
  (Test-Path -LiteralPath $root -PathType Container) -and
  (Test-Path -LiteralPath $db -PathType Leaf)) 'ORIGINAL_TASK_FILES_MISSING'
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
Checkouts
Main
$policyBefore=Policy

# Before first mutation the separate owner request, explicit linked approval,
# exact candidate checkout, current 2-lane ledger and original SID are proven.
$pre=Invoke-Pair $true 120000
Need ($pre.schema -ceq 'forge.f139.hybrid-v41.paired-owner-preflight.v1' -and
  $pre.candidate_sha -ceq $Target -and
  $pre.approval_comment_id -eq $event.comment.id -and
  $pre.source_transition_authorized -eq $false -and
  $pre.scientific_first_use -eq $false) 'PREPAUSE_PAIRED_AUTHORITY_INVALID'
Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
try {
  $lease=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($db,'.lock'),120000)
  Checkouts
  Main
  Need ((Policy) -ceq $policyBefore) 'PREPAUSE_POLICY_MOVED'
  $before=Ledger
  Need ($pre.original_head_seq -eq $before.head_seq -and
    $pre.original_head_sha256 -ceq $before.head_hash) 'PREPAUSE_HEAD_MOVED'
  $t=Task
  Need ([string]$t.State -cin @('Running','Ready') -and
    $t.Settings.Enabled -eq $true) 'ORIGINAL_TASK_MOVED_BEFORE_PAUSE'
  $paused=$true
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  if([string]$t.State -ceq 'Running'){
    Stop-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  }
  for($i=0;$i -lt 40;$i++){
    if(@(Children).Count -eq 0){break}
    Start-Sleep -Seconds 1
  }
  Disabled
  Unchanged
  $lease.Dispose();$lease=$null
  # The original remains disabled until a single bounded backup is verified.
  $receipt=Invoke-Pair $false 600000
  Need ($receipt.schema -ceq 'forge.f139.hybrid-v41.paired-owner-backup-only.v1' -and
    $receipt.run_id -eq $pre.run_id -and
    $receipt.backup_comment_id -eq $pre.backup_comment_id -and
    $receipt.approval_comment_id -eq $pre.approval_comment_id -and
    $receipt.candidate_sha -ceq $Target -and
    $receipt.original_head_seq -eq $before.head_seq -and
    $receipt.original_head_sha256 -ceq $before.head_hash -and
    $receipt.manifest_sha256 -cmatch '^[a-f0-9]{64}$' -and
    $receipt.independent_detached_restore_verified -eq $true -and
    $receipt.provider_archives_bytes_verified -eq $true -and
    $receipt.generation_binary_bytes_verified -eq $true -and
    $receipt.original_owner_mutations -eq 0 -and
    $receipt.source_transition_authorized -eq $false -and
    $receipt.hybrid_admission -eq $false -and
    $receipt.scientific_first_use -eq $false) 'FULL_COLD_RESTORE_RECEIPT_UNVERIFIED'
  Disabled
  Checkouts
  Unchanged
  Need ((Policy) -ceq $policyBefore) 'POST_BACKUP_POLICY_MOVED'
  Main
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $startAttempted=$true
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $final=Task
  Need ([string]$final.State -cin @('Ready','Running') -and
    $final.Settings.Enabled -eq $true) 'SAME_TASK_RESUME_UNVERIFIED'
  $resumed=$true
  Write-Host 'F139_HYBRID_V41_PAIRED_ORIGINAL_BACKUP=PASS'
  Write-Host ('F139_HYBRID_V41_SEALED_MANIFEST_SHA256='+[string]$receipt.manifest_sha256)
  Write-Host ('F139_HYBRID_V41_PRESERVED_LEDGER='+[string]$before.head_seq+':'+[string]$before.head_hash)
  Write-Host 'F139_HYBRID_V41_SAME_ORIGINAL_OWNER_RESUMED=PASS'
  Write-Host 'F139_HYBRID_V41_SOURCE_TRANSITION=FALSE'
  Write-Host 'F139_HYBRID_V41_SCIENTIFIC_FIRST_USE=FALSE'
} catch {
  $reason=$_.Exception.Message
  if($paused -and -not $startAttempted -and $backupChildCleared){
    try {
      if($lease){$lease.Dispose();$lease=$null}
      Disabled
      Checkouts
      Unchanged
      Need ((Policy) -ceq $policyBefore) 'ROLLBACK_POLICY_MOVED'
      Main
      Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      $startAttempted=$true
      Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      $result=Task
      Need ([string]$result.State -cin @('Ready','Running') -and
        $result.Settings.Enabled -eq $true) 'ROLLBACK_RESUME_FAILED'
      $resumed=$true
      Write-Warning 'F139_HYBRID_V41_BACKUP_FAILED_SAME_ORIGINAL_OWNER_RESUMED'
    } catch {
      Write-Warning 'F139_HYBRID_V41_SAFE_RESUME_UNVERIFIED_ORIGINAL_OWNER_HOLD'
    }
  }
  if($paused -and -not $resumed){
    throw ('F139_HYBRID_V41_ORIGINAL_OWNER_RECOVERY_HOLD: '+$reason)
  }
  throw ('F139_HYBRID_V41_BACKUP_NOT_ACCEPTED_NO_RELEASE: '+$reason)
} finally {
  if($lease){$lease.Dispose();$lease=$null}
}
