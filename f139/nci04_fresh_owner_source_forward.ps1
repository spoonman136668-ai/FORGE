# Exact original-SID one-time source forward for the EXISTING F139 task.
# PREPARE: stop+disable same task, qualify immutable source, create-only sign,
#          update action but NEVER enable/start.
# START:   independently require completed PREPARE owner run, then enable/start
#          the SAME task. No new scheduler/queue/worker/first-use.
[CmdletBinding()]
param(
  [ValidateSet('Prepare','Start')][string]$Phase,
  [Parameter(Mandatory)][string]$Target,
  [string]$Head = '',
  [int]$PrNumber = 0,
  [int64]$RegressionRun = 0,
  [int64]$SourceRun = 0,
  [int64]$RehearsalRun = 0,
  [int64]$PrepRun = 0
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='spoonman136668-ai/FORGE'
$old='c10625c1836d7f7a941cb81d32553857aae25536'
$oldTree='fec1166ed94e8cb95e47bcf50e312628d41d54ab'
$admission='408139c0a10fd4836a22422c8df041aa64dfa001'
$runId='44831323193'
$knownTerminal='9177021b1d78a084ac021fe02731b6232f319b537f527c5ad0532f7c47f2c812'
$taskName='FORGE-F139-UnifiedController'
$expectedTaskRoot=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$expectedDb=Join-Path $expectedTaskRoot ('f139-fresh-dev-'+$runId+'\state.sqlite')
$cert=Join-Path (Split-Path $expectedDb -Parent) 'fresh-original-owner-source-forward.json'
function Need([bool]$ok,[string]$why){
  if(-not $ok){throw ('F139_FRESH_OWNER_SOURCE_FORWARD_'+$why)}
}
function GetRemote([string]$path){
  $raw=@(& gh api $path 2>$null)
  Need ($LASTEXITCODE -eq 0 -and $raw.Count -gt 0) 'READONLY_PROVIDER_UNAVAILABLE'
  return ($raw -join [Environment]::NewLine | ConvertFrom-Json)
}
function ExactGit([string]$root,[string]$sha,[string]$tree){
  Need (Test-Path -LiteralPath $root -PathType Container) 'SOURCE_NOT_INSTALLED'
  $h=(& git -C $root rev-parse HEAD | Out-String).Trim()
  $t=(& git -C $root rev-parse 'HEAD^{tree}' | Out-String).Trim()
  $dirty=@(& git -C $root status --porcelain --untracked-files=all)
  $remote=(& git -C $root remote | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $h -ceq $sha -and $t -ceq $tree -and
        $dirty.Count -eq 0 -and -not $remote) 'CHECKOUT_SHA_TREE_OR_DIRTY'
}
function Arg($task,[string]$name){
  $m=[regex]::Match([string]$task.Actions[0].Arguments,'(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  Need $m.Success ('TASK_ARG_'+$name)
  return [string]$m.Groups[1].Value
}
function OwnerTask(){
  $t=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  Need (@($t.Actions).Count -eq 1 -and @($t.Triggers).Count -eq 3) 'SINGLE_TASK_TOPOLOGY'
  $sid=''
  try{$sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  Need ([string]$t.Principal.UserId -ieq $who.Name -or $sid -ceq $who.User.Value) 'ORIGINAL_SID_MISMATCH'
  return $t
}
function Controllers(){
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
}
function CheckLedger(){
  $code=@'
import sys
from pathlib import Path
from f139.local_controller import Database
db=Database.open_readonly(Path(sys.argv[1]))
try:
    db.verify()
    seq=db.meta()["head_seq"]
    assert seq == 9
    row=db.conn.execute("SELECT sha,kind FROM events WHERE seq=9").fetchone()
    assert row is not None and row["sha"] == sys.argv[2]
    assert row["kind"] == "FRESH_WORKER_PROVIDER_CUSTODY"
    tasks=list(db.conn.execute("SELECT stage FROM tasks"))
    assert len(tasks)==1 and tasks[0]["stage"] == "VERIFIED"
    assert db.conn.total_changes == 0
finally:
    db.close()
print("F139_FRESH_FORWARD_COLD_TERMINAL9=PASS")
'@
  $result=@($code | & python -B - $expectedDb $knownTerminal)
  Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1 -and
        $result[0] -ceq 'F139_FRESH_FORWARD_COLD_TERMINAL9=PASS') 'LEDGER_NOT_STABLE_NO_REPLAY'
}
function CheckCI([int64]$id,[string[]]$names,[string]$head){
  Need ($id -gt 0 -and $names.Count -ge 2) 'CI_ID_INVALID'
  $r=GetRemote ('repos/'+$repo+'/actions/runs/'+$id)
  $jobs=GetRemote ('repos/'+$repo+'/actions/runs/'+$id+'/jobs?per_page=100')
  $actual=@($jobs.jobs | ForEach-Object {[string]$_.name} | Sort-Object)
  $expected=@($names | Sort-Object)
  Need ($r.id -eq $id -and $r.head_sha -ceq $head -and
        $r.event -ceq 'pull_request' -and $r.run_attempt -eq 1 -and
        $r.status -ceq 'completed' -and $r.conclusion -ceq 'success' -and
        $jobs.total_count -eq $expected.Count -and
        ($actual -join '|') -ceq ($expected -join '|') -and
        @($jobs.jobs | Where-Object {$_.status -cne 'completed' -or $_.conclusion -cne 'success'}).Count -eq 0) 'EXACT_CI_UNQUALIFIED'
}
Need ($Target -cmatch '^[a-f0-9]{40}$' -and $Target -ceq $env:GITHUB_SHA -and
      $env:GITHUB_REPOSITORY -ceq $repo -and
      $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
      $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
      $env:GITHUB_REF -ceq 'refs/heads/main' -and
      $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
      $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
      -not $env:OPENAI_API_KEY -and -not $env:CLOUDFLARE_API_TOKEN -and
      $env:GH_TOKEN) 'EXACT_EXISTING_OWNER_EVENT_REQUIRED'
Need ([Security.Principal.WindowsPrincipal]::new(
      [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
      [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_OWNER_ADMIN_REQUIRED'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
Need ($event.action -ceq 'created' -and $event.issue.number -eq 1830 -and
      $event.issue.state -ceq 'open' -and
      $event.issue.user.login -ceq 'spoonman136668-ai' -and
      $event.sender.login -ceq 'spoonman136668-ai' -and
      $event.comment.user.login -ceq 'spoonman136668-ai' -and
      $event.comment.author_association -ceq 'OWNER' -and
      $null -eq $event.issue.PSObject.Properties['pull_request']) 'EVENT_NOT_ORIGINAL_OWNER'
$remoteComment=GetRemote ('repos/'+$repo+'/issues/comments/'+$event.comment.id)
Need ($remoteComment.id -eq $event.comment.id -and
      $remoteComment.body -ceq $event.comment.body -and
      $remoteComment.author_association -ceq 'OWNER' -and
      $remoteComment.user.login -ceq 'spoonman136668-ai') 'COMMENT_READBACK_FAILED'
$main=GetRemote ('repos/'+$repo+'/branches/main')
Need ($main.protected -eq $true -and $main.commit.sha -ceq $Target) 'PROTECTED_MAIN_MOVED'
$commit=GetRemote ('repos/'+$repo+'/git/commits/'+$Target)
Need ($commit.sha -ceq $Target -and $commit.tree.sha -cmatch '^[a-f0-9]{40}$') 'OWNER_MAIN_TREE_DRIFT'
ExactGit $env:GITHUB_WORKSPACE $Target $commit.tree.sha
$task=OwnerTask
Need ([IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe') 'ORIGINAL_ACTION_UNKNOWN'
Need ([IO.Path]::GetFullPath((Arg $task 'Database')) -ieq
      [IO.Path]::GetFullPath($expectedDb)) 'WRONG_LEDGER_PATH'
$root=Arg $task 'RepositoryRoot'
$py=Arg $task 'PythonExe'
$keyFile=Arg $task 'EncryptedKeyFile'
Need ((Test-Path -LiteralPath $py -PathType Leaf) -and
      (Test-Path -LiteralPath $keyFile -PathType Leaf)) 'OWNER_CREDENTIAL_ROUTE_MISSING'
$secure=Import-Clixml -LiteralPath $keyFile
Need ($secure -is [Security.SecureString]) 'DPAPI_KEY_OWNER_DRIFT'
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try{$env:F139_WORKER_HMAC_KEY=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}
finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
Need ($env:F139_WORKER_HMAC_KEY.Length -ge 32) 'OWNER_HMAC_KEY_INVALID'
try {
  if($Phase -ceq 'Prepare'){
    Need ($Head -cmatch '^[a-f0-9]{40}$' -and $PrNumber -ge 1863 -and
          $RegressionRun -gt 0 -and $SourceRun -gt 0 -and
          $RehearsalRun -gt 0 -and -not (Test-Path -LiteralPath $cert)) 'ONE_SHOT_PREPARE_DENIED'
    $expectedBody='F139-FRESH-OWNER-SOURCE-FORWARD '+$Target+' '+$Head+' '+$PrNumber+' '+$RegressionRun+' '+$SourceRun+' '+$RehearsalRun
    Need ($event.comment.body -ceq $expectedBody) 'SOURCE_BOUND_OWNER_COMMENT_INVALID'
    $pr=GetRemote ('repos/'+$repo+'/pulls/'+$PrNumber)
    Need ($pr.state -ceq 'closed' -and $pr.merged -eq $true -and
          $pr.merge_commit_sha -ceq $Target -and $pr.head.sha -ceq $Head -and
          $pr.user.login -ceq 'spoonman136668-ai') 'EXACT_MERGED_PR_REQUIRED'
    CheckCI $RegressionRun @('windows_f139','linux_f139','windows_genenv','linux_genenv','windows_native','linux_native','windows','linux') $Head
    CheckCI $SourceRun @('source (ubuntu-latest)','source (windows-latest)') $Head
    CheckCI $RehearsalRun @('development-rehearsal (ubuntu-latest)','development-rehearsal (windows-latest)') $Head
    Need ($task.Settings.Enabled -eq $true -and [string]$task.State -ceq 'Running' -and
          @(Controllers).Count -eq 1) 'ORIGINAL_RUNNING_OWNER_REQUIRED'
    ExactGit $root $old $oldTree
    CheckLedger
    # FIRST disable original task, THEN stop its child, then cold-verify again.
    Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
    for($i=0;$i -lt 80 -and @(Controllers).Count -ne 0;$i++){Start-Sleep -Milliseconds 250}
    Need (@(Controllers).Count -eq 0 -and
          (Get-ScheduledTask -TaskName $taskName).Settings.Enabled -eq $false) 'ORIGINAL_NOT_STOPPED_HOLD'
    CheckLedger
    $stage=Join-Path $expectedTaskRoot ('release-candidates\'+$Target)
    Need (-not(Test-Path -LiteralPath $stage)) 'TARGET_STAGE_ALREADY_EXISTS_NO_REPLAY'
    & git clone --no-local --no-checkout --quiet -- $env:GITHUB_WORKSPACE $stage
    Need ($LASTEXITCODE -eq 0) 'CREATE_ONLY_STAGE_FAILED'
    & git -C $stage checkout --quiet --detach $Target
    Need ($LASTEXITCODE -eq 0) 'CHECKOUT_FAILED'
    & git -C $stage remote remove origin
    Need ($LASTEXITCODE -eq 0) 'REMOVE_REMOTE_FAILED'
    ExactGit $stage $Target $commit.tree.sha
    $doc=@{
      schema='forge.f139.fresh-original-owner-source-forward.v1'
      admission_source_sha=$admission
      worker_release_sha=$old
      worker_release_tree=$oldTree
      owner_source_sha=$Target
      owner_source_tree=[string]$commit.tree.sha
      pr_number=[int]$PrNumber
      pr_head_sha=$Head
      owner_run_id=[int64]$env:GITHUB_RUN_ID
      owner_comment_id=[int64]$event.comment.id
      regression_run_id=$RegressionRun
      source_run_id=$SourceRun
      rehearsal_run_id=$RehearsalRun
      terminal_seq=9
      terminal_hash=$knownTerminal
      task_name=$taskName
      development_only=$true
      worker_release_unchanged=$true
      scientific_first_use=$false
      paid_model_calls=0
    } | ConvertTo-Json -Compress -Depth 5
    $code=@'
import json,os,sys
from pathlib import Path
from f139.nci04_native_contract import canonical
from f139.nci04_fresh_owner_source_forward import sign
v=json.load(sys.stdin)
v["owner_signature"]=sign(v,os.environ["F139_WORKER_HMAC_KEY"])
with Path(sys.argv[1]).open("xb") as f:
    f.write(canonical(v))
    f.flush()
    os.fsync(f.fileno())
print("F139_FRESH_FORWARD_CERTIFICATE=CREATE_ONLY_SIGNED")
'@
    $receipt=@($doc | & $py -B -c $code $cert)
    Need ($LASTEXITCODE -eq 0 -and $receipt.Count -eq 1 -and
          $receipt[0] -ceq 'F139_FRESH_FORWARD_CERTIFICATE=CREATE_ONLY_SIGNED') 'SIGNED_CERT_CREATE_FAILED'
    $a=[string]$task.Actions[0].Arguments
    Need ($a.Split(@($root),[StringSplitOptions]::None).Count -eq 3) 'SOURCE_PATH_NOT_UNIQUE'
    $newArgs=$a.Replace($root,$stage)
    Need ($newArgs -cne $a -and $newArgs.Contains($stage)) 'TASK_ACTION_NOT_REBOUND'
    $oldAction=$task.Actions[0]
    $newAction=New-ScheduledTaskAction -Execute ([string]$oldAction.Execute) -Argument $newArgs
    Set-ScheduledTask -TaskName $taskName -Action $newAction -ErrorAction Stop | Out-Null
    $after=OwnerTask
    Need ($after.Settings.Enabled -eq $false -and [string]$after.Actions[0].Arguments -ceq $newArgs -and
          @(Controllers).Count -eq 0) 'PREPARED_TASK_NOT_DISABLED'
    Write-Output 'F139_FRESH_OWNER_SOURCE_FORWARD_PREPARED_DISABLED=PASS'
    Write-Output 'F139_WORKER_DISPATCHES=ZERO'
    Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
  } else {
    Need ($PrepRun -gt 0 -and $event.comment.body -ceq
          ('F139-FRESH-OWNER-SOURCE-FORWARD-START '+$Target+' '+$PrepRun)) 'START_OWNER_COMMENT_INVALID'
    $doc=Get-Content -LiteralPath $cert -Raw -ErrorAction Stop | ConvertFrom-Json
    Need ($doc.owner_run_id -eq $PrepRun -and $doc.owner_source_sha -ceq $Target -and
          $doc.owner_source_tree -ceq $commit.tree.sha) 'START_CERTIFICATE_SOURCE_DRIFT'
    $prep=GetRemote ('repos/'+$repo+'/actions/runs/'+$PrepRun)
    $jobs=GetRemote ('repos/'+$repo+'/actions/runs/'+$PrepRun+'/jobs?per_page=100')
    Need ($prep.event -ceq 'issue_comment' -and $prep.head_sha -ceq $Target -and
          $prep.status -ceq 'completed' -and $prep.conclusion -ceq 'success' -and
          $prep.run_attempt -eq 1 -and
          @($jobs.jobs | Where-Object {$_.name -ceq 'fresh-original-owner-source-forward' -and
                 $_.conclusion -ceq 'success' -and $_.runner_name -ceq 'FORGE-CODEX-REMOTE'}).Count -eq 1) 'PREP_RUN_NOT_ACCEPTED'
    $signature=[string]$doc.owner_signature
    $unsigned=@{}
    foreach($prop in $doc.PSObject.Properties){if($prop.Name -cne 'owner_signature'){$unsigned[$prop.Name]=$prop.Value}}
    $code=@'
import json,os,sys
from f139.nci04_fresh_owner_source_forward import sign
v=json.load(sys.stdin)
assert sign(v,os.environ["F139_WORKER_HMAC_KEY"])==sys.argv[1]
print("F139_FORWARD_HMAC_VERIFIED")
'@
    $ok=@(($unsigned | ConvertTo-Json -Compress -Depth 5) | & $py -B -c $code $signature)
    Need ($LASTEXITCODE -eq 0 -and $ok.Count -eq 1 -and
          $ok[0] -ceq 'F139_FORWARD_HMAC_VERIFIED') 'FORWARD_HMAC_INVALID'
    Need ($task.Settings.Enabled -eq $false -and @(Controllers).Count -eq 0) 'PREP_TASK_NOT_DISABLED'
    $newroot=Arg $task 'RepositoryRoot'
    Need ([IO.Path]::GetFullPath($newroot) -ieq
          [IO.Path]::GetFullPath((Join-Path $expectedTaskRoot ('release-candidates\'+$Target)))) 'UNEXPECTED_TASK_SOURCE'
    ExactGit $newroot $Target $commit.tree.sha
    CheckLedger
    Enable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
    for($i=0;$i -lt 80 -and @(Controllers).Count -ne 1;$i++){Start-Sleep -Milliseconds 250}
    Need (@(Controllers).Count -eq 1 -and
          (Get-ScheduledTask -TaskName $taskName).Settings.Enabled -eq $true) 'ORIGINAL_TASK_START_NOT_VERIFIED'
    Write-Output 'F139_FRESH_ORIGINAL_SAME_TASK_SOURCE_FORWARDED=PASS'
    Write-Output 'F139_NO_NEW_CONTROLLER_OR_SCHEDULER=TRUE'
    Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
  }
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
}
