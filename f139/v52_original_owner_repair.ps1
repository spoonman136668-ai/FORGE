# V52 source-only forward repair for the ONE original Windows F139 task.
# Owner-issue event and exact CI identify authority. Detached rehearsal is
# nonmutating. Live is one-shot; after event1838 any uncertainty is HOLD.
param([Parameter(Mandatory=$true)][ValidateSet('Rehearse','Live')][string]$Mode,
      [Parameter(Mandatory=$true)][string]$Main)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$old='4ccbb84785a43e038453d6f2bda5415ecb364084'
$name='FORGE-F139-UnifiedController'
$existingHead='5a1ec5be32c4604e1c355629daf0f7f05749fb8201b161308d3606f0d3b6b8c6'
$backupPath=$null
$committedOrUncertain=$false
$disabled=$false
function Need([bool]$ok,[string]$code) {
  if(-not $ok) {throw ('F139_V52_REPAIR_'+$code)}
}
function GetJson([string]$route) {
  Need ($route.StartsWith('repos/spoonman136668-ai/FORGE/')) 'GITHUB_ROUTE'
  $lines=@(& gh api $route)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -gt 0) 'GITHUB_GET_FAILED'
  return (($lines -join "`n")|ConvertFrom-Json -Depth 32)
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
  $remote=GetJson ('repos/spoonman136668-ai/FORGE/issues/comments/'+$event.comment.id)
  Need ($remote.id -eq $event.comment.id -and
    $remote.user.login -ceq 'spoonman136668-ai' -and
    $remote.author_association -ceq 'OWNER' -and
    $remote.issue_url -ceq 'https://api.github.com/repos/spoonman136668-ai/FORGE/issues/807' -and
    $remote.created_at -ceq $event.comment.created_at -and
    $remote.updated_at -ceq $event.comment.updated_at -and
    [string]$remote.body -ceq $required) 'REMOTE_OWNER_INTENT_MOVED'
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
  $lines=@(& $python -B -m f139.nci04_v52_owner_forward_repair_cli --mode @cliArgs)
  Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
    [string]$lines[0] -clike ($prefix+'*')) 'NATIVE_ORIGINAL_REPAIR_DENIED'
  return ([string]$lines[0]).Substring($prefix.Length)|ConvertFrom-Json -Depth 20
}
# No source, task, policy, SQLite, or filesystem staging before exact original
# authenticated OWNER event and full main qualification.
Need ($env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:GITHUB_SHA -ceq $Main -and
  $Main -cmatch '^[a-f0-9]{40}$' -and
  -not $env:OPENAI_API_KEY) 'EXACT_FIRST_ATTEMPT_ORIGINAL_RUNNER'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
$parts=([string]$event.comment.body).Split(' ')
$priorRehearsal=if($Mode -ceq 'Live' -and $parts.Count -eq 4) {
  [int64]::Parse($parts[2])}else{0L}
$required=if($Mode -ceq 'Rehearse') {
  'F139-V52-REHEARSE '+$Main+' 43996174295'
}else{
  'F139-V52-LIVE '+$Main+' '+$priorRehearsal+' 43996174295'
}
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [int64]$event.comment.id -gt 6935011550 -and
  [string]$event.comment.body -ceq $required -and
  [string]$event.comment.created_at -ceq [string]$event.comment.updated_at) 'FRESH_SOURCE_BOUND_OWNER_INTENT'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($who).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_OWNER'
Need ((GitSource $env:GITHUB_WORKSPACE) -ceq $Main) 'CHECKOUT_SHA_DRIFT'
OwnerIntent
$mainRun=MainQualification
OwnerIntent
$originalPolicy=SourcePolicy
$task=OriginalRoute
$pref=InvokeNative @('preflight','--db',$database) 'F139_V52_PREFLIGHT='
Need ($pref.source_sha -ceq $old -and $pref.head_seq -eq 1837 -and
  $pref.head_sha256 -ceq $existingHead) 'ORIGINAL_EVENT1837_NOT_FROZEN'
if($Mode -ceq 'Rehearse') {
  $copy=Join-Path $env:RUNNER_TEMP ('f139-v52-original-rehearsal-'+$env:GITHUB_RUN_ID+'.sqlite')
  Need (-not (Test-Path -LiteralPath $copy)) 'REHEARSAL_COPY_ALREADY_USED'
  $r=InvokeNative @('rehearse','--db',$database,'--copy',$copy,
      '--target',$Main,'--owner-comment-id',([string]$event.comment.id),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$env:GITHUB_RUN_ID)) 'F139_V52_DETACHED_REHEARSAL='
  Need ($r.head_seq -eq 1839 -and $r.original_mutations -eq 0 -and
    $r.scientific_first_use -eq $false -and
    $r.target_source_sha -ceq $Main) 'DETACHED_SOURCE_ACTIVATION_FAILED'
  Need ((GitSource $root) -ceq $old -and
    (SourcePolicy) -ceq $originalPolicy -and
    (OriginalRoute).Settings.Enabled -eq $true) 'ORIGINAL_MUTATED_BY_REHEARSAL'
  Write-Output ('F139_V52_COPY_REHEARSAL_PASS='+($r|ConvertTo-Json -Depth 10 -Compress))
  Write-Output 'F139_V52_ORIGINAL_MUTATIONS=ZERO'
  return
}
# Live mode: independently prove a separate successful detached rehearsal run.
Need ($priorRehearsal -gt 0 -and [int64]$env:GITHUB_RUN_ID -ne $priorRehearsal) 'MISSING_DISTINCT_REHEARSAL'
$run=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$priorRehearsal)
Need ($run.id -eq $priorRehearsal -and
  $run.name -ceq 'FORGE F139 V52 original owner source-only recovery' -and
  $run.head_sha -ceq $Main -and $run.event -ceq 'issue_comment' -and
  $run.run_attempt -eq 1 -and $run.status -ceq 'completed' -and
  $run.conclusion -ceq 'success' -and
  $run.actor.login -ceq 'spoonman136668-ai') 'PREVIOUS_REHEARSAL_RUN_NOT_QUALIFIED'
$jobs=GetJson ('repos/spoonman136668-ai/FORGE/actions/runs/'+$priorRehearsal+'/jobs?per_page=100')
$copyJob=@($jobs.jobs|Where-Object {$_.name -ceq 'detached-owner-rehearsal'})
Need ($copyJob.Count -eq 1 -and $copyJob[0].conclusion -ceq 'success') 'REHEARSAL_JOB_MISSING'
$release=GetJson ('repos/spoonman136668-ai/FORGE/branches/f139-owner-release-'+$Main)
Need ($release.name -ceq ('f139-owner-release-'+$Main) -and
  $release.commit.sha -ceq $Main) 'EXACT_RELEASE_BRANCH_MISSING'
$stage=Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+$Main)
$binaryDir=Join-Path $env:LOCALAPPDATA ('FORGE-F139\genenv-source\'+$Main)
$binary=Join-Path $binaryDir 'f139-genenv-source.exe'
Need (-not (Test-Path -LiteralPath $stage) -and
  -not (Test-Path -LiteralPath $binaryDir)) 'SOURCE_CANDIDATE_ALREADY_STAGED'
$version=(& go version | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $version -ceq 'go version go1.23.12 windows/amd64') 'EXACT_GO_TOOLCHAIN'
& git clone --local --no-hardlinks --quiet $env:GITHUB_WORKSPACE $stage
Need ($LASTEXITCODE -eq 0 -and (GitSource $stage) -ceq $Main) 'STAGED_SOURCE_NOT_EXACT'
New-Item -ItemType Directory -Path $binaryDir -Force|Out-Null
Push-Location $stage
try {
  $env:GOOS='windows';$env:GOARCH='amd64';$env:CGO_ENABLED='0'
  & go build -trimpath -buildvcs=false -o $binary ./cmd/f139-genenv-source
  Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $binary -PathType Leaf) -and
    (Get-Item $binary).Length -gt 0 -and (Get-Item $binary).Length -le 16000000) 'SOURCE_BINARY_BUILD_FAILED'
}finally {Pop-Location}
Need ((GitSource $stage) -ceq $Main -and
  (SourcePolicy) -ceq $originalPolicy -and
  (OriginalRoute).Settings.Enabled -eq $true) 'PRELIVE_SOURCE_OR_POLICY_MOVED'
OwnerIntent
RemoteMain
$preview=Join-Path $env:RUNNER_TEMP ('f139-v52-live-practice-'+$env:GITHUB_RUN_ID+'.sqlite')
$r=InvokeNative @('rehearse','--db',$database,'--copy',$preview,
      '--target',$Main,'--owner-comment-id',([string]$event.comment.id),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal)) 'F139_V52_DETACHED_REHEARSAL='
Need ($r.head_seq -eq 1839 -and $r.original_mutations -eq 0) 'LIVE_REHEARSAL_NOT_PASS'
$backups=Join-Path $env:LOCALAPPDATA 'FORGE-F139\recovery-backups'
New-Item -ItemType Directory -Path $backups -Force | Out-Null
$backupPath=Join-Path $backups ('v52-event1837-'+$env:GITHUB_RUN_ID+'.sqlite')
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
  $env:F139_V52_NATIVE_LIVE_AUTHENTICATED='1'
  $b=InvokeNative @('backup','--db',$database,'--copy',$backupPath,
      '--target',$Main,'--owner-comment-id',([string]$event.comment.id),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal)) 'F139_V52_COLD_BACKUP='
  Need ($b.backup_sha256 -cmatch '^[a-f0-9]{64}$' -and
    $b.original.head_sha256 -ceq $existingHead) 'COLD_BACKUP_OR_HEAD_INVALID'
  OwnerIntent
  RemoteMain
  Need ((SourcePolicy) -ceq $originalPolicy -and
    (GitSource $root) -ceq $old -and (GitSource $stage) -ceq $Main) 'PRECOMMIT_SOURCE_OR_POLICY_MOVED'
  $committedOrUncertain=$true
  $receipt=InvokeNative @('commit','--db',$database,'--copy',$backupPath,
      '--target',$Main,'--owner-comment-id',([string]$event.comment.id),
      '--main-run-id',([string]$mainRun),
      '--rehearsal-run-id',([string]$priorRehearsal),
      '--backup-sha',([string]$b.backup_sha256)) 'F139_V52_ORIGINAL_EVENT1839='
  Need ($receipt.head_seq -eq 1839 -and $receipt.target_source_sha -ceq $Main) 'EVENT1839_COMMIT_UNVERIFIED'
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
    assert m["source_sha"]==sys.argv[2] and m["head_seq"]>=1839
    assert m["enabled"]==1 and m["legacy_suspended"]==1
    rows=list(db.conn.execute("SELECT seq,kind FROM events WHERE seq IN (1838,1839) ORDER BY seq"))
    assert len(rows)==2 and rows[0]["kind"]=="SOURCE_TRANSITION_ADMITTED"
    assert rows[1]["kind"]=="NATIVE_DEVELOPMENT_ACTIVATED"
    assert verify_native_activation(db) is True
    print("F139_V52_POSTSTART="+json.dumps({"source_sha":m["source_sha"],"head_seq":m["head_seq"],"head_hash":m["head_hash"],"native_development_activated":True,"scientific_first_use":False},sort_keys=True))
finally:
    db.close()
'@
  $output=@($check|& $python -B - $database $Main)
  Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1 -and
    [string]$output[0] -clike 'F139_V52_POSTSTART=*') 'POSTSTART_LEDGER_DRIFT'
  Write-Output ('F139_V52_ORIGINAL_SOURCE_REPAIRED='+([string]$output[0]).Substring('F139_V52_POSTSTART='.Length))
  Write-Output 'F139_V52_SAME_ORIGINAL_OWNER_RESTARTED=PASS'
  Write-Output 'F139_V52_SCIENTIFIC_FIRST_USE=FALSE'
  Write-Output 'F139_V52_NEW_CONTROLLER=FALSE'
}catch {
  if($disabled -or $committedOrUncertain){
    try {
      Disable-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
      Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue|Out-Null
    }catch {}
  }
  throw ('F139_V52_FORWARD_ONLY_HOLD_NO_REPLAY: '+$_.Exception.Message)
}finally{
  Remove-Item Env:F139_V52_NATIVE_LIVE_AUTHENTICATED -ErrorAction SilentlyContinue
  Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
}
