# V57 source-only forward repair for the ONE original Windows F139 task.
# Authenticated one-time issue assignment and exact CI identify owner intent.
# Detached rehearsal is nonmutating. Live is one-shot; after v47 source admission
# any uncertainty is HOLD. No duplicate controller or scheduler.
param([Parameter(Mandatory=$true)][ValidateSet('Rehearse','Live')][string]$Mode,
      [Parameter(Mandatory=$true)][string]$Main)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$old='f4d0eeebe18894ce2d16f63e915f356def692e17'
$name='FORGE-F139-UnifiedController'
$existingHead='bdf0e4cdb08902ad4e562552f1617922eaa9ad7107a58035bbfc1ae886e069b3'
$backupPath=$null
$committedOrUncertain=$false
$disabled=$false
function Need([bool]$ok,[string]$code) {
  if(-not $ok) {throw ('F139_V57_REPAIR_'+$code)}
}
function GetJson([string]$route) {
  Need ($route.StartsWith('repos/spoonman136668-ai/FORGE/')) 'GITHUB_ROUTE'
  # GitHub's original Windows runner may experience short API TCP resets.
  # Only repeat idempotent GETs; never retry owner writes, job admission,
  # first-use, SQLite commits or task mutations.  Exhaustion fails closed.
  for($attempt=1;$attempt -le 3;$attempt++) {
    $lines=@()
    $code=-1
    try {
      $lines=@(& gh api --method GET $route 2>$null)
      $code=$LASTEXITCODE
    } catch {
      $code=-1
    }
    if($code -eq 0 -and $lines.Count -gt 0) {
      try {
        return (($lines -join "`n")|ConvertFrom-Json -Depth 32 -ErrorAction Stop)
      } catch {
        Need $false 'GITHUB_GET_INVALID_JSON'
      }
    }
    if($attempt -lt 3) {
      Start-Sleep -Seconds (2*$attempt)
    }
  }
  Need $false 'GITHUB_GET_FAILED'
}
function Field($task,[string]$key) {
  $match=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $match.Success ('ORIGINAL_TASK_ARG_'+$key)
  return [string]$match.Groups[1].Value
}
function Children {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($database)})
}
function Task {
  $t=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try {
    $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
      Translate([Security.Principal.SecurityIdentifier]).Value
  } catch {}
  Need (@($t.Actions).Count -eq 1 -and
    @($t.Triggers).Count -eq 3 -and
    ([string]$t.Principal.UserId -ieq $who.Name -or
     $sid -ceq $who.User.Value) -and
    [IO.Path]::GetFileName([string]$t.Actions[0].Execute) -ieq 'powershell.exe') 'ORIGINAL_TASK_IDENTITY'
  return $t
}
function GitSource([string]$path) {
  $sha=(& git -C $path rev-parse HEAD | Out-String).Trim()
  $dirty=@(& git -C $path status --porcelain --untracked-files=all)
  Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0 -and
    $sha -cmatch '^[a-f0-9]{40}$') 'SOURCE_UNCLEAN'
  return $sha
}
function OwnerIntent {
  $remote=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$env:GITHUB_RUN_ID)
  Need ([int64]$remote.id -eq [int64]$env:GITHUB_RUN_ID -and
    $remote.name -ceq 'FORGE F139 V54 original owner model-free source recovery' -and
    $remote.path -ceq '.github/workflows/f139-v54-original-owner-release.yml' -and
    $remote.event -ceq 'issue_comment' -and
    $remote.actor.login -ceq 'spoonman136668-ai' -and
    $remote.head_branch -ceq 'main' -and
    $remote.head_sha -ceq $Main -and
    $remote.run_attempt -eq 1 -and
    $remote.status -ceq 'in_progress' -and
    $null -eq $remote.conclusion) 'ORIGINAL_OWNER_WORKFLOW_RUN_NOT_AUTHENTIC'
  $issue=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  Need ($issue.state -ceq 'open' -and
    @($issue.assignees).Count -eq 1 -and
    $issue.assignees[0].login -ceq 'spoonman136668-ai') 'ORIGINAL_OWNER_ASSIGNMENT_NOT_CURRENT'
}
function SourcePolicy {
  $p=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  Need ($p.state -ceq 'open' -and $p.user.login -ceq 'spoonman136668-ai') 'ORIGINAL_POLICY_ISSUE'
  $obj=[string]$p.body|ConvertFrom-Json -Depth 20
  Need ($obj.source_sha -ceq $old -and $obj.enabled -eq $true -and
    @($obj.lanes).Count -eq 3 -and
    $obj.lanes[0] -ceq 'Wingless' -and
    $obj.lanes[1] -ceq 'Yggdrasil' -and
    $obj.lanes[2] -ceq 'TTT-Hybrid' -and
    $obj.scientific_first_use -eq $false -and
    $obj.new_controller -eq $false -and
    $obj.new_scheduler -eq $false -and
    $obj.new_queue -eq $false -and
    $obj.paid_model_calls -eq 0) 'ORIGINAL_POLICY_SOURCE_OR_SCOPE'
  return [string]$p.body
}
function RemoteMain {
  $b=GetJson 'repos/spoonman136668-ai/FORGE/branches/main'
  Need ($b.protected -eq $true -and $b.commit.sha -ceq $Main) 'PROTECTED_MAIN_DRIFT'
}
function MainQualification {
  RemoteMain
  $all=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs?head_sha='+$Main+'&event=push&branch=main&per_page=100')
  $qualified=@($all.workflow_runs|Where-Object {$_.name -ceq 'FORGE public Linux and Windows qualification'})
  Need ($qualified.Count -eq 1) 'EXACT_EIGHT_JOB_QUALIFICATION'
  $run=$qualified[0]
  Need ($run.head_sha -ceq $Main -and $run.head_branch -ceq 'main' -and
    $run.run_attempt -eq 1 -and $run.actor.login -ceq 'spoonman136668-ai' -and
    $run.status -ceq 'completed' -and $run.conclusion -ceq 'success') 'MAIN_CI_NOT_PASS'
  $jobs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$run.id+'/jobs?per_page=100')
  $expected=@('linux_genenv','linux_native','linux_f139','windows_genenv','windows_native','windows_f139','linux','windows')
  Need ($jobs.total_count -eq 8 -and @($jobs.jobs).Count -eq 8 -and
    @($jobs.jobs|Where-Object {$_.status -ceq 'completed' -and $_.conclusion -ceq 'success'}).Count -eq 8 -and
    @($jobs.jobs|Where-Object {$expected -contains $_.name}).Count -eq 8) 'FULL_8_OF_8_REGRESSION'
  return [int64]$run.id
}
function OriginalRoute {
  $task=Task
  Need ([string]$task.State -cin @('Running','Ready') -and
    $task.Settings.Enabled -eq $true) 'ORIGINAL_TASK_DISABLED_BEFORE_REQUEST'
  $script:database=Field $task 'Database'
  $script:root=Field $task 'RepositoryRoot'
  $script:python=Field $task 'PythonExe'
  $wrapper=Field $task 'File'
  Need (([IO.Path]::GetFullPath($database) -ieq
    [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite'))) -and
    (Test-Path -LiteralPath $database -PathType Leaf) -and
    (Test-Path -LiteralPath $python -PathType Leaf) -and
    [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
    [IO.Path]::GetFullPath($root) -ieq
    [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$old))) -and
    (GitSource $root) -ceq $old) 'ORIGINAL_ROUTE_OR_SOURCE_DRIFT'
  Need (@(Children).Count -le 1) 'MULTIPLE_ORIGINAL_CONTROLLERS'
  return $task
}
function InvokeNative([string[]]$cliArgs,[string]$prefix) {
  $env:PYTHONPATH=$env:GITHUB_WORKSPACE
  $lines=@(& $python -B -m f139.nci04_v57_owner_release_cli --mode @cliArgs)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
    [string]$lines[0] -clike ($prefix+'*')) 'NATIVE_ORIGINAL_REPAIR_DENIED'
  return ([string]$lines[0]).Substring($prefix.Length)|ConvertFrom-Json -Depth 20
}

function MechanismHash([string]$checkout) {
  Need ((GitSource $checkout) -ceq $Main) 'MECHANISM_SOURCE_DIRTY'
  $code=@'
from f139.nci04_genenv_owner_backend import generation_mechanism
from f139.nci04_native_contract import digest
print(digest(generation_mechanism()))
'@
  $priorPath=$env:PYTHONPATH
  try {
    $env:PYTHONPATH=$checkout
    $lines=@($code|& $python -B -)
    Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
      [string]$lines[0] -cmatch '^[a-f0-9]{64}$') 'GENERATOR_MECHANISM_HASH'
    return [string]$lines[0]
  }finally {$env:PYTHONPATH=$priorPath}
}
function TemporaryBinary([string]$checkout) {
  $version=(& go version | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and
    $version -ceq 'go version go1.23.12 windows/amd64') 'EXACT_GO_TOOLCHAIN'
  $temporary=Join-Path $env:RUNNER_TEMP ('f139-v57-genenv-rehearsal-'+$env:GITHUB_RUN_ID+'.exe')
  Need (-not (Test-Path -LiteralPath $temporary)) 'REHEARSAL_BINARY_COLLISION'
  Push-Location $checkout
  try {
    $env:GOOS='windows';$env:GOARCH='amd64';$env:CGO_ENABLED='0'
    & go build -trimpath -buildvcs=false -o $temporary ./cmd/f139-genenv-source
    Need ($LASTEXITCODE -eq 0 -and
      (Test-Path -LiteralPath $temporary -PathType Leaf) -and
      (Get-Item -LiteralPath $temporary).Length -gt 0 -and
      (Get-Item -LiteralPath $temporary).Length -le 16000000) 'REHEARSAL_BINARY_BUILD'
  } finally {Pop-Location}
  return (Get-FileHash -LiteralPath $temporary -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
}
# No source, task, policy, SQLite, or filesystem staging before exact original
# authenticated OWNER event and full main qualification.
Need ($env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_WORKFLOW_REF -ceq 'spoonman136668-ai/FORGE/.github/workflows/f139-v54-original-owner-release.yml@refs/heads/main' -and
  ($env:GITHUB_JOB -ceq 'detached-owner-rehearsal' -or $env:GITHUB_JOB -ceq 'original-owner-forward-repair') -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:GITHUB_SHA -ceq $Main -and
  $Main -cmatch '^[a-f0-9]{40}$' -and
  -not $env:OPENAI_API_KEY) 'EXACT_FIRST_ATTEMPT_ORIGINAL_RUNNER'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json -Depth 20
$priorRehearsal=[int64]$env:GITHUB_RUN_ID
Need ($priorRehearsal -gt 44076995053 -and
  $event.action -ceq 'created' -and
  $event.repository.full_name -ceq 'spoonman136668-ai/FORGE' -and
  $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $event.issue.state -ceq 'open' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  [string]$event.comment.body -ceq ('F139-V54-OWNER-RELEASE '+$Main+' V57') -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  (($Mode -ceq 'Rehearse' -and $env:GITHUB_JOB -ceq 'detached-owner-rehearsal') -or
   ($Mode -ceq 'Live' -and $env:GITHUB_JOB -ceq 'original-owner-forward-repair'))) 'FRESH_SOURCE_BOUND_OWNER_ASSIGNMENT'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($who).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_OWNER'
Need ((GitSource $env:GITHUB_WORKSPACE) -ceq $Main) 'CHECKOUT_SHA_DRIFT'
OwnerIntent
$mainRun=MainQualification
OwnerIntent
$originalPolicy=SourcePolicy
$task=OriginalRoute
$pref=InvokeNative @('preflight','--db',$database) 'F139_V57_PREFLIGHT='
Need ($pref.source_sha -ceq $old -and $pref.head_seq -eq 1857 -and
  $pref.verified_historical_tasks -ge 154 -and
  $pref.custodied_negative_tasks -ge 56) 'ORIGINAL_EVENT1857_HISTORY_NOT_AUTHENTICATED'
if($Mode -ceq 'Rehearse') {
  $binarySha=TemporaryBinary $env:GITHUB_WORKSPACE
  $mechanismSha=MechanismHash $env:GITHUB_WORKSPACE
  $copy=Join-Path $env:RUNNER_TEMP ('f139-v57-original-rehearsal-'+$env:GITHUB_RUN_ID+'.sqlite')
  Need (-not (Test-Path -LiteralPath $copy)) 'REHEARSAL_COPY_ALREADY_USED'
  $r=InvokeNative @('rehearse','--db',$database,'--copy',$copy,
      '--target',$Main,'--owner-run-id',([string]$env:GITHUB_RUN_ID),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$env:GITHUB_RUN_ID),
      '--binary-sha',$binarySha,'--mechanism-sha',$mechanismSha) 'F139_V57_DETACHED_REHEARSAL='
  Need ($r.head_seq -eq ($pref.head_seq+2) -and $r.original_mutations -eq 0 -and
    $r.scientific_first_use -eq $false -and
    $r.target_source_sha -ceq $Main) 'DETACHED_SOURCE_ACTIVATION_FAILED'
  Need ((GitSource $root) -ceq $old -and
    (SourcePolicy) -ceq $originalPolicy -and
    (OriginalRoute).Settings.Enabled -eq $true) 'ORIGINAL_MUTATED_BY_REHEARSAL'
  Write-Output ('F139_V57_COPY_REHEARSAL_PASS='+($r|ConvertTo-Json -Depth 10 -Compress))
  Write-Output 'F139_V57_ORIGINAL_MUTATIONS=ZERO'
  return
}
# Same authenticated owner run, two distinct jobs. Live may only follow a
# COMPLETED detached rehearsal on the original Windows runner.
OwnerIntent
$jobs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$priorRehearsal+'/jobs?per_page=100')
Need ($jobs.total_count -eq 2 -and @($jobs.jobs).Count -eq 2) 'EXACT_OWNER_RUN_JOB_SET'
$copyJob=@($jobs.jobs|Where-Object {$_.name -ceq 'detached-owner-rehearsal'})
$liveJob=@($jobs.jobs|Where-Object {$_.name -ceq 'original-owner-forward-repair'})
Need ($copyJob.Count -eq 1 -and $liveJob.Count -eq 1 -and
  $copyJob[0].status -ceq 'completed' -and
  $copyJob[0].conclusion -ceq 'success' -and
  $copyJob[0].runner_name -ceq 'FORGE-CODEX-REMOTE' -and
  $liveJob[0].status -ceq 'in_progress' -and
  $liveJob[0].runner_name -ceq 'FORGE-CODEX-REMOTE') 'WORKFLOW_RUN_REHEARSAL_NOT_VERIFIED'
$stage=Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$Main)
$binaryDir=Join-Path $env:LOCALAPPDATA ('FORGE-F139\genenv-source\'+$Main)
$binary=Join-Path $binaryDir 'f139-genenv-source.exe'
# A previous authorized job can leave create-only staging behind even when
# original SQLite and the task were never touched. Do not erase or overwrite it.
# Accept only the exact clean, non-linked pinned source and independently
# reproduce the exact binary bytes on the original toolchain.
$hasStage=Test-Path -LiteralPath $stage
$hasBinaryDir=Test-Path -LiteralPath $binaryDir
$version=(& go version | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $version -ceq 'go version go1.23.12 windows/amd64') 'EXACT_GO_TOOLCHAIN'
if($hasStage) {
  $item=Get-Item -LiteralPath $stage -Force -ErrorAction Stop
  Need ($item.PSIsContainer -and
    -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and
    (GitSource $stage) -ceq $Main) 'EXISTING_STAGE_SOURCE_NOT_EXACT'
  $untracked=@(& git -C $stage ls-files --others --ignored --exclude-standard)
  Need ($LASTEXITCODE -eq 0 -and $untracked.Count -eq 0) 'EXISTING_STAGE_IGNORED_OR_UNTRACKED'
} else {
  Need (-not $hasBinaryDir) 'ORPHAN_BINARY_WITHOUT_SOURCE'
  & git clone --local --no-hardlinks --quiet $env:GITHUB_WORKSPACE $stage
  Need ($LASTEXITCODE -eq 0 -and (GitSource $stage) -ceq $Main) 'STAGED_SOURCE_NOT_EXACT'
}
$buildBinary=Join-Path $env:RUNNER_TEMP ('f139-v57-genenv-verify-'+$env:GITHUB_RUN_ID+'.exe')
Need (-not (Test-Path -LiteralPath $buildBinary)) 'SOURCE_BINARY_TEMP_COLLISION'
Push-Location $stage
try {
  $env:GOOS='windows';$env:GOARCH='amd64';$env:CGO_ENABLED='0'
  & go build -trimpath -buildvcs=false -o $buildBinary ./cmd/f139-genenv-source
  Need ($LASTEXITCODE -eq 0 -and
    (Test-Path -LiteralPath $buildBinary -PathType Leaf) -and
    (Get-Item -LiteralPath $buildBinary).Length -gt 0 -and
    (Get-Item -LiteralPath $buildBinary).Length -le 16000000) 'SOURCE_BINARY_BUILD_FAILED'
}finally {Pop-Location}
$verifiedBinaryHash=(Get-FileHash -LiteralPath $buildBinary -Algorithm SHA256 -ErrorAction Stop).Hash
$binarySha=$verifiedBinaryHash.ToLowerInvariant()
$mechanismSha=MechanismHash $stage
if($hasBinaryDir) {
  $dir=Get-Item -LiteralPath $binaryDir -Force -ErrorAction Stop
  Need ($hasStage -and $dir.PSIsContainer -and
    -not ($dir.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'EXISTING_BINARY_DIR_INVALID'
  $entries=@(Get-ChildItem -LiteralPath $binaryDir -Force -ErrorAction Stop)
  Need ($entries.Count -eq 1 -and
    $entries[0].Name -ceq 'f139-genenv-source.exe' -and
    -not ($entries[0].Attributes -band [IO.FileAttributes]::ReparsePoint) -and
    (Test-Path -LiteralPath $binary -PathType Leaf) -and
    (Get-Item -LiteralPath $binary).Length -gt 0 -and
    (Get-Item -LiteralPath $binary).Length -le 16000000 -and
    (Get-FileHash -LiteralPath $binary -Algorithm SHA256 -ErrorAction Stop).Hash -ceq $verifiedBinaryHash) 'EXISTING_BINARY_BYTES_NOT_REPRODUCIBLE'
  Remove-Item -LiteralPath $buildBinary -ErrorAction Stop
} else {
  New-Item -ItemType Directory -Path $binaryDir -ErrorAction Stop -Force|Out-Null
  Need (-not (Test-Path -LiteralPath $binary)) 'SOURCE_BINARY_DESTINATION_EXISTS'
  Move-Item -LiteralPath $buildBinary -Destination $binary -ErrorAction Stop
  Need ((Get-FileHash -LiteralPath $binary -Algorithm SHA256 -ErrorAction Stop).Hash -ceq $verifiedBinaryHash) 'NEW_SOURCE_BINARY_BYTES_DRIFT'
}
Need ((GitSource $stage) -ceq $Main -and
  (Test-Path -LiteralPath $binary -PathType Leaf)) 'VERIFIED_STAGE_NOT_STABLE'
Need ((GitSource $stage) -ceq $Main -and
  (SourcePolicy) -ceq $originalPolicy -and
  (OriginalRoute).Settings.Enabled -eq $true) 'PRELIVE_SOURCE_OR_POLICY_MOVED'
OwnerIntent
RemoteMain
$preview=Join-Path $env:RUNNER_TEMP ('f139-v57-live-practice-'+$env:GITHUB_RUN_ID+'.sqlite')
$r=InvokeNative @('rehearse','--db',$database,'--copy',$preview,
      '--target',$Main,'--owner-run-id',([string]$env:GITHUB_RUN_ID),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal),
      '--binary-sha',$binarySha,'--mechanism-sha',$mechanismSha) 'F139_V57_DETACHED_REHEARSAL='
Need ($r.head_seq -eq ($pref.head_seq+2) -and $r.original_mutations -eq 0) 'LIVE_REHEARSAL_NOT_PASS'
# Provision exactly one source-addressed owner release ref after qualified
# detached rehearsal, source checks and byte-reproducible local binary.
OwnerIntent
RemoteMain
$releaseRef='refs/heads/f139-owner-release-'+$Main
& gh api --method POST repos/spoonman136668-ai/FORGE/git/refs -f ('ref='+$releaseRef) -f ('sha='+$Main) --silent
Need ($LASTEXITCODE -eq 0) 'CREATE_ONLY_OWNER_RELEASE_REF_DENIED'
$release=GetJson ('repos/spoonman136668-ai/FORGE/branches/f139-owner-release-'+$Main)
Need ($release.name -ceq ('f139-owner-release-'+$Main) -and
  $release.commit.sha -ceq $Main) 'EXACT_RELEASE_REF_READBACK_DRIFT'
$backups=Join-Path $env:LOCALAPPDATA 'FORGE-F139\recovery-backups'
New-Item -ItemType Directory -Path $backups -Force | Out-Null
$backupPath=Join-Path $backups ('v57-event1857-'+$env:GITHUB_RUN_ID+'.sqlite')
Need (-not (Test-Path -LiteralPath $backupPath)) 'COLD_BACKUP_COLLISION'
try {
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $disabled=$true
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
  $quiesced=$false
  for($i=0;$i -lt 30;$i++){
    $t=Task
    if([string]$t.State -ceq 'Disabled' -and
       $t.Settings.Enabled -eq $false -and
       @(Children).Count -eq 0){$quiesced=$true;break}
    Start-Sleep -Seconds 1
  }
  Need $quiesced 'ORIGINAL_TASK_NOT_STOPPED'
  $env:F139_V57_NATIVE_LIVE_AUTHENTICATED='1'
  # The owner CLI authenticates executable and mechanism pins even in
  # backup mode; never reach live quiescence with missing required flags.
  $b=InvokeNative @('backup','--db',$database,'--copy',$backupPath,
      '--target',$Main,'--owner-run-id',([string]$env:GITHUB_RUN_ID),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal),
      '--binary-sha',$binarySha,'--mechanism-sha',$mechanismSha) 'F139_V57_COLD_BACKUP='
  Need ($b.backup_sha256 -cmatch '^[a-f0-9]{64}$' -and
    $b.original.head_seq -eq 1857 -and
    $b.original.source_sha -ceq $old) 'COLD_BACKUP_OR_HEAD_INVALID'
  OwnerIntent
  RemoteMain
  Need ((SourcePolicy) -ceq $originalPolicy -and
    (GitSource $root) -ceq $old -and (GitSource $stage) -ceq $Main -and
    (MechanismHash $stage) -ceq $mechanismSha -and
    (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $binarySha) 'PRECOMMIT_SOURCE_OR_POLICY_MOVED'
  $committedOrUncertain=$true
  $receipt=InvokeNative @('commit','--db',$database,'--copy',$backupPath,
      '--target',$Main,'--owner-run-id',([string]$env:GITHUB_RUN_ID),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal),
      '--backup-sha',([string]$b.backup_sha256),
      '--binary-sha',$binarySha,'--mechanism-sha',$mechanismSha) 'F139_V57_ORIGINAL_EVENT1859='
  Need ($receipt.head_seq -eq ($b.original.head_seq+2) -and $receipt.target_source_sha -ceq $Main) 'V47_ACTIVATION_COMMIT_UNVERIFIED'
  $replaceCount=$originalPolicy.Split(@($old),[StringSplitOptions]::None).Count
  Need ($replaceCount -eq 2) 'ORIGINAL_POLICY_SOURCE_NOT_UNIQUE'
  $changed=$originalPolicy.Replace($old,$Main)
  & gh api --method PATCH repos/spoonman136668-ai/FORGE/issues/807 -f ('body='+$changed) --silent
  Need ($LASTEXITCODE -eq 0) 'POLICY_WRITE_UNCERTAIN_HOLD'
  $policy1=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  $policy2=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  Need ([string]$policy1.body -ceq $changed -and
    [string]$policy2.body -ceq $changed) 'POLICY_POSTWRITE_HOLD'
  $newArgs=[string]$task.Actions[0].Arguments
  Need ($newArgs.Split(@($root),[StringSplitOptions]::None).Count -eq 3) 'ORIGINAL_ROOT_REFERENCES_CHANGED'
  $newArgs=$newArgs.Replace($root,$stage)
  $workdir=[string]$task.Actions[0].WorkingDirectory
  if($workdir -ceq $root){$workdir=$stage}
  if($workdir){
    $act=New-ScheduledTaskAction -Execute ([string]$task.Actions[0].Execute) -Argument $newArgs -WorkingDirectory $workdir
  }else{
    $act=New-ScheduledTaskAction -Execute ([string]$task.Actions[0].Execute) -Argument $newArgs
  }
  Set-ScheduledTask -TaskName $name -Action $act -ErrorAction Stop | Out-Null
  $retargeted=Task
  Need ([string]$retargeted.State -ceq 'Disabled' -and
    $retargeted.Settings.Enabled -eq $false -and
    [string]$retargeted.Actions[0].Arguments -ceq $newArgs -and
    @(Children).Count -eq 0 -and
    (GitSource $stage) -ceq $Main) 'RETARGETED_ORIGINAL_TASK_NOT_HELD'
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  Start-ScheduledTask -TaskName $name -ErrorAction Stop|Out-Null
  $running=$false
  for($i=0;$i -lt 30;$i++){
    $t=Task
    if([string]$t.State -cin @('Running','Ready') -and
       $t.Settings.Enabled -eq $true -and
       @(Children).Count -eq 1){$running=$true;break}
    Start-Sleep -Seconds 1
  }
  Need $running 'ORIGINAL_OWNER_PROCESS_NOT_RESTARTED'
  $script:disabled=$false
  $check=@'
import json,os,sys
from pathlib import Path
from f139.local_controller import Database
from f139.nci04_owner_ledger import verify_native_activation
p=Path(sys.argv[1]).resolve()
db=Database.open_readonly(p)
try:
    m=db.meta()
    assert m["source_sha"]==sys.argv[2] and m["head_seq"]>=1859
    assert m["enabled"]==1 and m["legacy_suspended"]==1
    rows=list(db.conn.execute("SELECT seq,kind FROM events WHERE seq IN (1858,1859) ORDER BY seq"))
    assert len(rows)==2 and rows[0]["seq"]==1858 and rows[0]["kind"]=="SOURCE_TRANSITION_ADMITTED"
    assert rows[1]["seq"]==1859 and rows[1]["kind"]=="NATIVE_DEVELOPMENT_ACTIVATED"
    assert verify_native_activation(db) is True
    print("F139_V57_POSTSTART="+json.dumps({"source_sha":m["source_sha"],"head_seq":m["head_seq"],"head_hash":m["head_hash"],"native_development_activated":True,"scientific_first_use":False},sort_keys=True))
finally:
    db.close()
'@
  $output=@($check|& $python -B - $database $Main)
  Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1 -and
    [string]$output[0] -clike 'F139_V57_POSTSTART=*') 'POSTSTART_LEDGER_DRIFT'
  Write-Output ('F139_V57_ORIGINAL_SOURCE_REPAIRED='+([string]$output[0]).Substring('F139_V57_POSTSTART='.Length))
  Write-Output 'F139_V57_SAME_ORIGINAL_OWNER_RESTARTED=PASS'
  Write-Output 'F139_V57_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Output 'F139_V57_NEW_CONTROLLER=FALSE'
}catch {
  if($disabled -or $committedOrUncertain){
    try {
      Disable-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    }catch {}
  }
  throw ('F139_V57_FORWARD_ONLY_HOLD_NO_REPLAY: '+$_.Exception.Message)
}finally{
  Remove-Item Env:F139_V57_NATIVE_LIVE_AUTHENTICATED -ErrorAction SilentlyContinue
  Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
}
