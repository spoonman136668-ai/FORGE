# Authenticated original-task af204acc -> 4ccbb847 event1836 live transition.
# This is a ONE-SHOT owner release, not a new controller or scheduler.
# Before SQLite commit entry: recover old original only after pristine readback.
# After commit entry (including uncertainty): HOLD, never restore old SQLite.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$old='af204acc983719b382bc8daf2216ec6733ca3ee7'
$targetFrozen='4ccbb84785a43e038453d6f2bda5415ecb364084'
$name='FORGE-F139-UnifiedController'
$disabled=$false
$commitEntered=$false
$activated=$false
$originalArgs=$null
$originalRoot=$null
$originalPolicy=$null
$database=$null
$python=$null
$preimage=$null
$stage=$null
$task=$null
function Need([bool]$ok,[string]$code) {
  if(-not $ok) {throw ('F139_V46_INSTALL_'+$code)}
}
function TaskArg($t,[string]$key) {
  $match=[regex]::Match([string]$t.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $match.Success ('ORIGINAL_TASK_ARG_'+$key)
  return [string]$match.Groups[1].Value
}
function GitSource([string]$folder) {
  $sha=(& git -C $folder rev-parse HEAD | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $sha -cmatch '^[0-9a-f]{40}$') 'GIT_SHA_MISSING'
  $dirty=@(& git -C $folder status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'DIRTY_SOURCE'
  return $sha
}
function RemoteMain {
  $sha=(& gh api repos/spoonman136668-ai/FORGE/branches/main --jq '.commit.sha' | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $sha -ceq $env:GITHUB_SHA) 'PROTECTED_MAIN_MOVED'
}
function RemotePolicy {
  $raw=@(& gh api repos/spoonman136668-ai/FORGE/issues/807 --jq '.body')
  Need ($LASTEXITCODE -eq 0 -and $raw.Count -eq 1) 'OWNER_POLICY_READ'
  return [string]$raw[0]
}
function SourceOld {
  Need ((GitSource $originalRoot) -ceq $old) 'INSTALLED_SOURCE_DRIFT'
}
function PolicyOld {
  Need ((RemotePolicy) -ceq $originalPolicy) 'OWNER_POLICY_MOVED'
}
function OwnerChildren {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $null -ne $database -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
}
function Held {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$t.State -ceq 'Disabled' -and
    $t.Settings.Enabled -eq $false -and
    @(OwnerChildren).Count -eq 0) 'ORIGINAL_NOT_QUIESCED'
}
function Ledger([string]$expectedSource,[int]$expectedSeq) {
  $code=@'
import sqlite3,sys
from pathlib import Path
path=Path(sys.argv[1]).resolve()
con=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,isolation_level=None,timeout=10)
con.execute("PRAGMA query_only=ON")
assert con.execute("PRAGMA quick_check").fetchone()[0]=="ok"
m=con.execute("SELECT source_sha,enabled,legacy_suspended,head_seq,head_hash FROM meta WHERE id=1").fetchone()
assert m is not None and m[0]==sys.argv[2] and m[1]==1 and m[2]==1 and m[3]==int(sys.argv[3]) and len(m[4])==64
print(str(m[3])+":"+str(m[4]))
con.close()
'@
  $result=@($code | & $python -B - $database $expectedSource ([string]$expectedSeq))
  Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1 -and
    [string]$result[0] -cmatch '^[0-9]+:[0-9a-f]{64}$') 'LEDGER_IDENTITY_DRIFT'
  return [string]$result[0]
}

# Fail before any task/policy/SQLite mutation unless a fresh, source-bound
# GitHub owner release was created AFTER the V44 success. CLI reauthenticates.
Need ($Target -ceq $targetFrozen -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_SHA -cmatch '^[a-f0-9]{40}$' -and
  -not $env:OPENAI_API_KEY) 'EXACT_OWNER_FIRST_ATTEMPT_REQUIRED'
Need ((GitSource $env:GITHUB_WORKSPACE) -ceq $env:GITHUB_SHA) 'WORKFLOW_CHECKOUT_DRIFT'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
$required='F139-V46-LIVE-INSTALL '+$env:GITHUB_SHA+' '+$Target+' 6917006014'
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [string]$event.comment.body -ceq $required -and
  [int64]$event.comment.id -gt 6917006014) 'FRESH_OWNER_RELEASE_INTENT'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($who).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ADMIN_REQUIRED'
$data=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$root=Join-Path $data 'release-candidates'
$stage=Join-Path $root $Target
$binary=Join-Path $data ('genenv-source\'+$Target+'\f139-genenv-source.exe')
$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
Need ([string]$task.State -cin @('Running','Ready') -and
  $task.Settings.Enabled -eq $true -and
  @($task.Actions).Count -eq 1 -and
  @($task.Triggers).Count -eq 3 -and
  [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe') 'ORIGINAL_TASK_IDENTITY'
$sid=''
try { $sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
  Translate([Security.Principal.SecurityIdentifier]).Value } catch {}
Need ([string]$task.Principal.UserId -ieq $who.Name -or
  $sid -ceq $who.User.Value) 'ORIGINAL_OWNER_SID_DRIFT'
$originalArgs=[string]$task.Actions[0].Arguments
$originalRoot=TaskArg $task 'RepositoryRoot'
$database=TaskArg $task 'Database'
$python=TaskArg $task 'PythonExe'
$wrapper=TaskArg $task 'File'
$expectedRoot=Join-Path $root $old
Need ([IO.Path]::GetFullPath($originalRoot) -ieq
  [IO.Path]::GetFullPath($expectedRoot) -and
  [IO.Path]::GetFullPath($database) -ieq
  [IO.Path]::GetFullPath((Join-Path $data 'state.sqlite')) -and
  [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
  ($originalArgs -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') -and
  (Test-Path -LiteralPath $python -PathType Leaf)) 'ORIGINAL_TASK_ARGS_DRIFT'
SourceOld
$originalPolicy=RemotePolicy
$p=$originalPolicy|ConvertFrom-Json
Need ($p.schema -ceq 'forge.f139.native-autonomy-feed-owner-policy.v1' -and
  $p.enabled -eq $true -and $p.source_sha -ceq $old -and
  @($p.lanes).Count -eq 3 -and
  $p.lanes[0] -ceq 'Wingless' -and
  $p.lanes[1] -ceq 'Yggdrasil' -and
  $p.lanes[2] -ceq 'TTT-Hybrid' -and
  $p.max_issue_creations_per_cycle -eq 2 -and
  $p.scientific_first_use -eq $false -and
  $p.paid_model_calls -eq 0 -and
  $p.accepted_ref_mutations -eq 0 -and
  $p.new_controller -eq $false -and
  $p.new_scheduler -eq $false -and
  $p.new_queue -eq $false) 'THREE_LANE_POLICY_PREIMAGE'
RemoteMain
$preimage=Ledger $old 1835
Need ($preimage -ceq '1835:2c06bb327ee8e6dd8e6d9b766d3673170dc80e93fca6e7497f89b466d19c1c83') 'FROZEN_EVENT1835_DRIFT'

# V45+V44+V43 original-host custody, real saved copy and protected-main
# eight-job qualification: read-only check before any old-task operation.
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
$env:PYTHONDONTWRITEBYTECODE='1'
Push-Location $env:GITHUB_WORKSPACE
try {
  $pre=@(& $python -B -m f139.nci04_v46_live_source_commit --target $Target --preflight-only)
  Need ($LASTEXITCODE -eq 0 -and $pre.Count -eq 1 -and
    $pre[0] -cmatch '^F139_V46_PRECOMMIT_PREFLIGHT=') 'PRECOMMIT_CUSTODY_UNQUALIFIED'
} finally {Pop-Location}

# Create-only exact ancestry stage; never overwrite an unknown partial folder.
Need ((Test-Path -LiteralPath $root -PathType Container) -and
  -not([IO.FileAttributes]::ReparsePoint -band
    (Get-Item -LiteralPath $root).Attributes)) 'STAGE_PARENT_UNSAFE'
if(-not(Test-Path -LiteralPath $stage)) {
  $scratch=Join-Path $root ('v46-stage-'+$env:GITHUB_RUN_ID)
  Need (-not(Test-Path -LiteralPath $scratch)) 'EXISTING_PARTIAL_STAGE_HOLD'
  & git clone --quiet --no-hardlinks --no-checkout $env:GITHUB_WORKSPACE $scratch
  Need ($LASTEXITCODE -eq 0) 'SOURCE_STAGE_CLONE_FAILED'
  & git -C $scratch checkout --quiet --detach $Target
  Need ($LASTEXITCODE -eq 0 -and
    (GitSource $scratch) -ceq $Target) 'SOURCE_STAGE_CHECKOUT_FAILED'
  Move-Item -LiteralPath $scratch -Destination $stage -ErrorAction Stop
}
Need ((GitSource $stage) -ceq $Target -and
  (Test-Path -LiteralPath (Join-Path $stage 'scripts\Run-FORGE-F139.ps1') -PathType Leaf)) 'EXACT_TARGET_STAGE_REQUIRED'
$existingBinNeedsSourceProof=(Test-Path -LiteralPath $binary -PathType Leaf)
if(-not(Test-Path -LiteralPath $binary -PathType Leaf)) {
  $binRoot=Split-Path -Parent $binary
  Need (-not(Test-Path -LiteralPath $binRoot)) 'UNKNOWN_PARTIAL_BINARY_STAGE'
  New-Item -ItemType Directory -Path $binRoot -Force:$false | Out-Null
  $oldToolchain=$env:GOTOOLCHAIN
  $oldGoproxy=$env:GOPROXY
  $oldSumdb=$env:GOSUMDB
  try {
    $env:GOTOOLCHAIN='local'
    $env:GOPROXY='off'
    $env:GOSUMDB='off'
    Push-Location $stage
    try {
      & go build -trimpath -o $binary ./cmd/f139-genenv-source
      Need ($LASTEXITCODE -eq 0) 'LOCAL_OFFLINE_GENENV_BUILD_FAILED'
    } finally {Pop-Location}
  } finally {
    $env:GOTOOLCHAIN=$oldToolchain
    $env:GOPROXY=$oldGoproxy
    $env:GOSUMDB=$oldSumdb
  }
}
Need ((Test-Path -LiteralPath $binary -PathType Leaf) -and
  (Get-Item -LiteralPath $binary).Length -gt 0 -and
  (GitSource $stage) -ceq $Target) 'BINARY_OR_TARGET_NOT_READY'
# An existing executable is never trusted by path or nonzero length alone.
# Rebuild from the exact clean target checkout without network or toolchain
# downloads, then compare hashes. Mismatch is a PRECOMMIT HOLD.
if($existingBinNeedsSourceProof) {
  $proofBin=Join-Path $data ('v46-bin-proof-'+$env:GITHUB_RUN_ID+'.exe')
  Need (-not(Test-Path -LiteralPath $proofBin)) 'EXISTING_BINARY_PROOF_COLLISION'
  $oldGoToolchain=$env:GOTOOLCHAIN
  $oldGoProxy=$env:GOPROXY
  $oldGoSumDb=$env:GOSUMDB
  try {
    $env:GOTOOLCHAIN='local'
    $env:GOPROXY='off'
    $env:GOSUMDB='off'
    Push-Location $stage
    try {
      & go build -trimpath -o $proofBin ./cmd/f139-genenv-source
      Need ($LASTEXITCODE -eq 0 -and
        (Test-Path -LiteralPath $proofBin -PathType Leaf)) 'EXACT_SOURCE_BINARY_REBUILD_FAILED'
    } finally {Pop-Location}
    $originalDigest=(Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash
    $rebuildDigest=(Get-FileHash -LiteralPath $proofBin -Algorithm SHA256).Hash
    Need ($originalDigest -ceq $rebuildDigest) 'EXISTING_BINARY_NOT_SOURCE_BOUND'
  } finally {
    $env:GOTOOLCHAIN=$oldGoToolchain
    $env:GOPROXY=$oldGoProxy
    $env:GOSUMDB=$oldGoSumDb
    Remove-Item -LiteralPath $proofBin -Force -ErrorAction SilentlyContinue
  }
}
$lastTaskArgs=$originalArgs
$lease=$null
try {
  # Use the original controller's kernel mutex before any task control.
  Add-Type -Path (Join-Path $env:GITHUB_WORKSPACE 'f139/F139OriginalOwnerMutex.cs') -ErrorAction Stop
  $lease=[F139OriginalOwnerMutex]::Acquire(
    [IO.Path]::ChangeExtension($database,'.lock'),120000)
  Need ((Ledger $old 1835) -ceq $preimage) 'LEDGER_MOVED_BEFORE_PAUSE'
  SourceOld
  PolicyOld
  RemoteMain
  $disabled=$true
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $taskNow=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  if([string]$taskNow.State -ceq 'Running'){
    Stop-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  }
  for($n=0;$n -lt 40;$n++){
    if(@(OwnerChildren).Count -eq 0){break}
    Start-Sleep -Seconds 1
  }
  Held
  Need ((Ledger $old 1835) -ceq $preimage) 'PRECOMMIT_LEDGER_DRIFT'
  $lease.Dispose();$lease=$null

  # The irreversible threshold: never replay an uncertain commit attempt.
  $commitEntered=$true
  Push-Location $env:GITHUB_WORKSPACE
  try {
    $output=@(& $python -B -m f139.nci04_v46_live_source_commit --target $Target)
  } finally {Pop-Location}
  Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1 -and
    $output[0] -cmatch '^F139_V46_ORIGINAL_COMMIT_HOLD=') 'SOURCE_COMMIT_UNVERIFIED_HOLD'
  $receipt=$output[0].Substring('F139_V46_ORIGINAL_COMMIT_HOLD='.Length)|ConvertFrom-Json
  Need ($receipt.schema -ceq 'forge.f139.v46.original-event1836-source-commit-hold.v1' -and
    $receipt.target_source_sha -ceq $Target -and
    $receipt.workflow_sha -ceq $env:GITHUB_SHA -and
    $receipt.new_head_seq -eq 1836 -and
    $receipt.source_committed_once -eq $true -and
    $receipt.original_task_still_disabled -eq $true -and
    $receipt.original_policy_unchanged -eq $true -and
    $receipt.database_rollback_authorized -eq $false -and
    $receipt.scientific_first_use -eq $false -and
    $receipt.new_dispatches -eq 0) 'POSTCOMMIT_ORIGINAL_RECEIPT_HOLD'
  Held
  $posthead=Ledger $Target 1836
  Need ($posthead -ceq ('1836:'+[string]$receipt.new_head_sha256)) 'POSTCOMMIT_EVENT1836_MISMATCH'
  SourceOld
  PolicyOld
  RemoteMain

  # Preserve ALL prior policy fields; change source_sha only.
  Need ($originalPolicy.Split(@($old),[StringSplitOptions]::None).Count -eq 2) 'SOURCE_NOT_UNIQUE_IN_POLICY'
  $updatedPolicy=$originalPolicy.Replace($old,$Target)
  & gh api --method PATCH repos/spoonman136668-ai/FORGE/issues/807 -f ('body='+$updatedPolicy) --silent
  Need ($LASTEXITCODE -eq 0) 'POLICY_PATCH_UNCERTAIN_HOLD'
  Need ((RemotePolicy) -ceq $updatedPolicy -and
    (RemotePolicy) -ceq $updatedPolicy) 'NEW_POLICY_READBACK_HOLD'
  Held
  Need ($originalArgs.Split(@($originalRoot),[StringSplitOptions]::None).Count -eq 3) 'TASK_ORIGINAL_ROOT_REFERENCES_INVALID'
  $newArgs=$originalArgs.Replace($originalRoot,$stage)
  $priorAction=$task.Actions[0]
  $workingDir=[string]$priorAction.WorkingDirectory
  if($workingDir -ceq $originalRoot){$workingDir=$stage}
  if($workingDir){
    $newAction=New-ScheduledTaskAction -Execute ([string]$priorAction.Execute) -Argument $newArgs -WorkingDirectory $workingDir
  } else {
    $newAction=New-ScheduledTaskAction -Execute ([string]$priorAction.Execute) -Argument $newArgs
  }
  Set-ScheduledTask -TaskName $name -Action $newAction -ErrorAction Stop|Out-Null
  $retargeted=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  Need ([string]$retargeted.State -ceq 'Disabled' -and
    $retargeted.Settings.Enabled -eq $false -and
    [string]$retargeted.Actions[0].Arguments -ceq $newArgs -and
    [string]$retargeted.Principal.UserId -ceq [string]$task.Principal.UserId -and
    @($retargeted.Triggers).Count -eq 3) 'ORIGINAL_TASK_RETARGET_HOLD'
  Need ((RemotePolicy) -ceq $updatedPolicy -and
    (Ledger $Target 1836) -ceq $posthead) 'PREACTIVATION_STATE_DRIFT'
  RemoteMain
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $live=$null
  for($i=0;$i -lt 30;$i++){
    $live=Get-ScheduledTask -TaskName $name -ErrorAction Stop
    if($live.Settings.Enabled -eq $true -and
       [string]$live.State -cin @('Ready','Running') -and
       @(OwnerChildren).Count -eq 1){break}
    Start-Sleep -Seconds 1
  }
  Need ($live.Settings.Enabled -eq $true -and
    [string]$live.State -cin @('Ready','Running') -and
    [string]$live.Actions[0].Arguments -ceq $newArgs -and
    @(OwnerChildren).Count -eq 1 -and
    (RemotePolicy) -ceq $updatedPolicy) 'LIVE_OWNER_PROCESS_OR_POLICY_NOT_VERIFIED'
  # A healthy owner may append event1837+ as soon as it starts.
  # Verify the immutable 1836 event proof instead of requiring the current
  # head to remain frozen at 1836 after activation.
  $anchor=@(& $python -B -m f139.nci04_v46_live_source_commit --target $Target --poststart-readonly --event1836-sha ([string]$receipt.new_head_sha256))
  Need ($LASTEXITCODE -eq 0 -and $anchor.Count -eq 1 -and
    [string]$anchor[0] -ceq 'F139_V46_LIVE_EVENT1836_ANCHOR=PASS') 'LIVE_EVENT1836_OR_SOURCE_UNVERIFIED'
  $activated=$true
  Write-Output ('F139_V46_ACTIVATED_ORIGINAL_OWNER='+($receipt|ConvertTo-Json -Depth 16 -Compress))
  Write-Output 'F139_V46_SAME_ORIGINAL_TASK_ACTIVATED=PASS'
  Write-Output 'F139_V46_NEW_CONTROLLER=FALSE'
  Write-Output 'F139_V46_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Output 'F139_V46_UNATTENDED_SCIENTIFIC_PROGRESS=UNVERIFIED'
} catch {
  $message=$_.Exception.Message
  if($lease){$lease.Dispose();$lease=$null}
  if($disabled -and -not $commitEntered) {
    try {
      Held
      SourceOld
      PolicyOld
      Need ((Ledger $old 1835) -ceq $preimage) 'OLD_PREIMAGE_CHANGED_RECOVERY_HOLD'
      Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Write-Warning 'F139_V46_PRECOMMIT_ORIGINAL_SAFELY_RESUMED'
    } catch {
      Write-Warning 'F139_V46_PRECOMMIT_RECOVERY_UNVERIFIED_HOLD'
    }
  } elseif($commitEntered -and -not $activated) {
    # No uncertain replay, automatic rollback or old-source restart.
    try {
      Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    } catch {}
    Write-Warning 'F139_V46_POSTCOMMIT_FORWARD_REPAIR_ONLY_HOLD'
  }
  throw ('F139_V46_INSTALL_NOT_ACCEPTED: '+$message)
} finally {
  if($lease){$lease.Dispose();$lease=$null}
}
