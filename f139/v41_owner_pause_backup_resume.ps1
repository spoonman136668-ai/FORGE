# Exact owner-authorized original V40 task pause, private V41 backup and same-task resume.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$old='2c7caad5a4502d4b874a11d57207a35cf033eb08'
$name='FORGE-F139-UnifiedController'
$paused=$false
$startAttempted=$false
$resumed=$false
$lease=$null
$before=$null
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('F139_V41_MAINTENANCE_'+$why)}}
function OriginalArg($task,[string]$key){
  $m=[regex]::Match([string]$task.Actions[0].Arguments,'(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success 'TASK_ARGUMENT_MISSING'
  return $m.Groups[1].Value
}
function Policy(){
  $x=& gh api repos/spoonman136668-ai/FORGE/issues/807
  Need ($LASTEXITCODE -eq 0) 'POLICY_GET_FAILED'
  $p=($x -join [Environment]::NewLine)|ConvertFrom-Json
  $b=[string]$p.body|ConvertFrom-Json
  Need ($p.state -ceq 'open' -and $p.user.login -ceq 'spoonman136668-ai' -and
    $b.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
    $b.source_sha -ceq $old -and $b.enabled -eq $true -and
    @($b.lanes).Count -eq 2 -and $b.lanes[0] -ceq 'Wingless' -and
    $b.lanes[1] -ceq 'Yggdrasil' -and $b.scientific_first_use -eq $false -and
    $b.paid_model_calls -eq 0 -and $b.new_controller -eq $false -and
    $b.new_scheduler -eq $false -and $b.new_queue -eq $false) 'POLICY_DRIFT'
  return [string]$p.body
}
function Main(){
  $sha=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha' | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $sha -ceq $Target) 'PROTECTED_MAIN_MOVED'
}
function Installed(){
  $head=(& git -C $root rev-parse HEAD|Out-String).Trim()
  $dirty=@(& git -C $root status --porcelain --untracked-files=all)
  Need ($head -ceq $old -and $dirty.Count -eq 0 -and
    (Test-Path -LiteralPath $database -PathType Leaf) -and
    (Test-Path -LiteralPath $python -PathType Leaf)) 'INSTALLED_OWNER_CHANGED'
}
function Ledger(){
  $py=@'
import json,sqlite3,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve()
con=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,isolation_level=None,timeout=10)
con.row_factory=sqlite3.Row
con.execute("PRAGMA query_only=ON")
assert con.execute("PRAGMA quick_check").fetchone()[0]=="ok"
m=dict(con.execute("SELECT source_sha,enabled,legacy_suspended,head_seq,head_hash FROM meta WHERE id=1").fetchone())
assert m["source_sha"]==sys.argv[2] and m["enabled"]==1 and m["legacy_suspended"]==1
assert m["head_seq"]>=1826 and len(m["head_hash"])==64
print(json.dumps(m,sort_keys=True,separators=(",",":")))
con.close()
'@
  $lines=@($py|& $python -B - $database $old)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1) 'LEDGER_READ_UNVERIFIED'
  return ($lines[0]|ConvertFrom-Json)
}
function Children(){
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
}
function Disabled(){
  $task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$task.State -ceq 'Disabled' -and
    $task.Settings.Enabled -eq $false -and @(Children).Count -eq 0) 'OWNER_NOT_QUIESCED'
}
function Unchanged(){
  $now=Ledger
  Need ($null -ne $before -and $now.source_sha -ceq $before.source_sha -and
    $now.head_seq -eq $before.head_seq -and
    $now.head_hash -ceq $before.head_hash) 'ORIGINAL_LEDGER_CHANGED'
}
Need ($env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $Target -cmatch '^[a-f0-9]{40}$' -and
  $Target -ceq $env:GITHUB_SHA -and
  (& git rev-parse HEAD|Out-String).Trim() -ceq $Target -and
  @(& git status --porcelain --untracked-files=all).Count -eq 0) 'RUNNER_OR_SOURCE_DRIFT'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
Need ($event.action -ceq 'created' -and $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [int64]$event.comment.id -gt 0 -and
  [string]$event.comment.body -ceq ('F139-V41-PAUSE-BACKUP-RESUME '+$Target)) 'OWNER_COMMENT_DENIED'
$id=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($id)
Need ($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_REQUIRED'
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
Need ([string]$task.State -cin @('Running','Ready') -and $task.Settings.Enabled -eq $true -and
  @($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
  [string]$task.Actions[0].Arguments -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') 'TASK_TOPOLOGY_DRIFT'
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
  Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
Need ([string]$task.Principal.UserId -ieq $id.Name -or
  $sid -ceq $id.User.Value) 'OWNER_SID_DRIFT'
$root=OriginalArg $task 'RepositoryRoot'
$database=OriginalArg $task 'Database'
$python=OriginalArg $task 'PythonExe'
Need ([IO.Path]::GetFullPath($database) -ceq
  (Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite')) 'ORIGINAL_DATABASE_PATH'
Installed
$policyBefore=Policy
Main
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
$pre=@(& $python -B -m f139.nci04_v41_owner_cold_backup --db $database --target $Target --preflight-only)
Need ($LASTEXITCODE -eq 0 -and $pre.Count -eq 1 -and
  $pre[0] -cmatch '^F139_V41_MAINTENANCE_PREFLIGHT=') 'PREMUTATION_APPROVAL_OR_CI_DENIED'
Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
try {
  # One bounded kernel wait for a genuinely idle original owner tick.
  $lease=[F139OriginalOwnerMutex]::Acquire([IO.Path]::ChangeExtension($database,'.lock'),120000)
  Installed
  Main
  Need ((Policy) -ceq $policyBefore) 'POLICY_MOVED_BEFORE_PAUSE'
  $before=Ledger
  $task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$task.State -cin @('Ready','Running') -and
    $task.Settings.Enabled -eq $true) 'TASK_MOVED_BEFORE_PAUSE'
  $paused=$true
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  if([string]$task.State -ceq 'Running'){
    Stop-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  }
  for($i=0;$i -lt 40;$i++){
    if(@(Children).Count -eq 0){break}
    Start-Sleep -Seconds 1
  }
  Disabled
  Unchanged
  $lease.Dispose()
  $lease=$null
  $out=@(& $python -B -m f139.nci04_v41_owner_cold_backup --db $database --target $Target)
  Need ($LASTEXITCODE -eq 0 -and $out.Count -eq 1 -and
    $out[0] -cmatch '^F139_V41_BACKUP_ONLY=') 'BACKUP_OR_RESTORE_FAILED'
  $receipt=$out[0].Substring('F139_V41_BACKUP_ONLY='.Length)|ConvertFrom-Json
  Need ($receipt.schema -ceq 'forge.f139.v41.original-host-backup-only.v1' -and
    $receipt.target_sha -ceq $Target -and
    $receipt.detached_restore_verified -eq $true -and
    $receipt.original_head_seq -eq $before.head_seq -and
    $receipt.original_head_sha256 -ceq $before.head_hash -and
    $receipt.owner_mutations -eq 0 -and
    $receipt.new_dispatches -eq 0 -and
    $receipt.source_transition_authorized -eq $false -and
    $receipt.scientific_first_use -eq $false) 'COLD_RECEIPT_NOT_QUALIFIED'
  Disabled
  Installed
  Unchanged
  Need ((Policy) -ceq $policyBefore) 'POLICY_MOVED_AFTER_BACKUP'
  Main
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $startAttempted=$true
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $final=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$final.State -cin @('Ready','Running') -and
    $final.Settings.Enabled -eq $true) 'SAME_OWNER_RESUME_UNVERIFIED'
  $resumed=$true
  Write-Host ('F139_V41_SEALED_MANIFEST_SHA256='+[string]$receipt.manifest_sha256)
  Write-Host ('F139_V41_PRESERVED_PRE_RESUME_LEDGER='+[string]$before.head_seq+':'+[string]$before.head_hash)
  Write-Host 'F139_V41_ORIGINAL_BACKUP_DETACHED_RESTORE=PASS'
  Write-Host 'F139_V41_EXISTING_V40_OWNER_RESUMED=PASS'
  Write-Host 'F139_V41_SCIENTIFIC_FIRST_USE=FALSE'
} catch {
  $reason=$_.Exception.Message
  if($paused -and -not $startAttempted){
    try {
      if($lease){$lease.Dispose();$lease=$null}
      Disabled
      Installed
      Unchanged
      Need ((Policy) -ceq $policyBefore) 'ROLLBACK_POLICY_DRIFT'
      Main
      Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      $startAttempted=$true
      Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      $current=Get-ScheduledTask -TaskName $name -ErrorAction Stop
      Need ([string]$current.State -cin @('Ready','Running') -and
        $current.Settings.Enabled -eq $true) 'ROLLBACK_RESUME_UNVERIFIED'
      $resumed=$true
      Write-Warning 'F139_V41_BACKUP_FAILED_SAME_OWNER_SAFELY_RESUMED'
    } catch {
      Write-Warning 'F139_V41_OWNER_RECOVERY_HOLD_OR_UNVERIFIED_MANUAL_ATTENTION'
    }
  }
  if($paused -and -not $resumed){throw ('F139_V41_OWNER_RESUME_UNVERIFIED: '+$reason)}
  throw ('F139_V41_BACKUP_NOT_ACCEPTED_ORIGINAL_OWNER_UNCHANGED: '+$reason)
} finally {
  if($lease){$lease.Dispose();$lease=$null}
}
