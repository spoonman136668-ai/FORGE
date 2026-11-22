# Owner-only V2 source forward on the SAME original FORGE-F139 task.
# PREPARE is a one-time DISABLE/STOP followed by cold audit and create-only
# versioned certificate; START needs a separately completed owner PREPARE run.
# Never creates a task, worker, scheduler, feed issue or scientific first-use.
[CmdletBinding()]
param(
  [ValidateSet('Prepare','Start')][string]$Phase,
  [Parameter(Mandatory)][string]$Target,
  [string]$Head = '',
  [int]$PrNumber = 0,
  [int64]$RegressionRun = 0,
  [int64]$SourceRun = 0,
  [int64]$RehearsalRun = 0,
  [int64]$TerminalSeq = 0,
  [string]$TerminalHash = '',
  [int64]$PrepRun = 0
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='spoonman136668-ai/FORGE'
$previousMain='f24251e0d95938e593a54c1577a34efadc8080d8'
$prScope=1869
$runId='44831323193'
$taskName='FORGE-F139-UnifiedController'
$root=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$db=Join-Path $root ('f139-fresh-dev-'+$runId+'\state.sqlite')
$oldCert=Join-Path (Split-Path $db -Parent) 'fresh-original-owner-source-forward.json'
$cert=Join-Path (Split-Path $db -Parent) 'fresh-original-owner-source-forward-v2.json'
$prepPrefix='F139-FRESH-OWNER-SOURCE-FORWARD-V2 '
$startPrefix='F139-FRESH-OWNER-SOURCE-FORWARD-V2-START '
function Need([bool]$ok,[string]$reason) {
  if(-not $ok){throw ('F139_V2_OWNER_FORWARD_'+$reason)}
}
function Remote([string]$route) {
  $value=@(& gh api $route 2>$null)
  Need ($LASTEXITCODE -eq 0 -and $value.Count -gt 0) 'PROVIDER_READ_FAILED'
  return ($value -join [Environment]::NewLine | ConvertFrom-Json)
}
function ExactGit([string]$path,[string]$sha,[string]$tree,[switch]$AllowRemote) {
  Need (Test-Path -LiteralPath $path -PathType Container) 'SOURCE_MISSING'
  $actual=(& git -C $path rev-parse HEAD | Out-String).Trim()
  $actualTree=(& git -C $path rev-parse 'HEAD^{tree}' | Out-String).Trim()
  $dirty=@(& git -C $path status --porcelain --untracked-files=all)
  $remotes=(& git -C $path remote | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $actual -ceq $sha -and
        $actualTree -ceq $tree -and $dirty.Count -eq 0 -and
        ($AllowRemote -or -not $remotes)) 'SOURCE_SHA_TREE_OR_DIRTY'
}
function TaskArg($task,[string]$name) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  Need $m.Success ('TASK_ARG_'+$name)
  return [string]$m.Groups[1].Value
}
function OwnerTask {
  $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $sid=''
  try{$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
  Need (@($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
        ([string]$task.Principal.UserId -ieq $who.Name -or
        $sid -ceq $who.User.Value) -and
        [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe') 'ORIGINAL_SINGLE_TASK_SID_INVALID'
  Need ([IO.Path]::GetFullPath((TaskArg $task 'Database')) -ieq
        [IO.Path]::GetFullPath($db)) 'ORIGINAL_DATABASE_DRIFT'
  return $task
}
function Owners {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
}
function CheckCI([int64]$id,[string[]]$names,[string]$sha) {
  $run=Remote ('repos/'+$repo+'/actions/runs/'+$id)
  $response=Remote ('repos/'+$repo+'/actions/runs/'+$id+'/jobs?per_page=100')
  $actual=@($response.jobs | ForEach-Object {[string]$_.name} | Sort-Object)
  $expected=@($names | Sort-Object)
  Need ($run.id -eq $id -and $run.head_sha -ceq $sha -and
        $run.event -ceq 'pull_request' -and $run.run_attempt -eq 1 -and
        $run.status -ceq 'completed' -and $run.conclusion -ceq 'success' -and
        $response.total_count -eq $expected.Count -and
        ($actual -join '|') -ceq ($expected -join '|') -and
        @($response.jobs | Where-Object {$_.status -cne 'completed' -or $_.conclusion -cne 'success'}).Count -eq 0) 'EXACT_FINAL_HEAD_CI_UNQUALIFIED'
}
function Encoded([string]$json) {
  Need ($json.Length -gt 2 -and $json.Length -le 8192) 'METADATA_SIZE_INVALID'
  return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
}
Need ($Target -cmatch '^[a-f0-9]{40}$' -and
      $Target -ceq $env:GITHUB_SHA -and
      $env:GITHUB_REPOSITORY -ceq $repo -and
      $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
      $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
      $env:GITHUB_REF -ceq 'refs/heads/main' -and
      $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
      $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
      -not $env:OPENAI_API_KEY -and -not $env:CLOUDFLARE_API_TOKEN -and
      $env:GH_TOKEN) 'EXACT_OWNER_EVENT_REQUIRED'
Need ([Security.Principal.WindowsPrincipal]::new(
      [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
      [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_REQUIRED'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
Need ($event.action -ceq 'created' -and $event.issue.number -eq 1830 -and
      $event.issue.state -ceq 'open' -and
      $event.issue.user.login -ceq 'spoonman136668-ai' -and
      $event.sender.login -ceq 'spoonman136668-ai' -and
      $event.comment.user.login -ceq 'spoonman136668-ai' -and
      $event.comment.author_association -ceq 'OWNER' -and
      $null -eq $event.issue.PSObject.Properties['pull_request']) 'NOT_ORIGINAL_OWNER'
$comment=Remote ('repos/'+$repo+'/issues/comments/'+$event.comment.id)
Need ($comment.id -eq $event.comment.id -and
      $comment.body -ceq $event.comment.body -and
      $comment.author_association -ceq 'OWNER' -and
      $comment.user.login -ceq 'spoonman136668-ai') 'OWNER_COMMENT_READBACK_DRIFT'
$main=Remote ('repos/'+$repo+'/branches/main')
$commit=Remote ('repos/'+$repo+'/git/commits/'+$Target)
Need ($main.protected -eq $true -and $main.commit.sha -ceq $Target -and
      $commit.sha -ceq $Target -and
      [string]$commit.tree.sha -cmatch '^[a-f0-9]{40}$') 'PROTECTED_SOURCE_DRIFT'
ExactGit $env:GITHUB_WORKSPACE $Target ([string]$commit.tree.sha) -AllowRemote
$task=OwnerTask
Need (Test-Path -LiteralPath $oldCert -PathType Leaf) 'ORIGINAL_SIGNED_CERT_MISSING'
$python=TaskArg $task 'PythonExe'
$keyfile=TaskArg $task 'EncryptedKeyFile'
Need (Test-Path -LiteralPath $python -PathType Leaf) 'PYTHON_MISSING'
Need (Test-Path -LiteralPath $keyfile -PathType Leaf) 'ORIGINAL_OWNER_DPAPI_KEY_MISSING'
$secure=Import-Clixml -LiteralPath $keyfile
Need ($secure -is [Security.SecureString]) 'OWNER_DPAPI_SCOPE_DRIFT'
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try{$env:F139_WORKER_HMAC_KEY=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}
finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
Need ($env:F139_WORKER_HMAC_KEY.Length -ge 32) 'OWNER_KEY_INVALID'
try {
  if($Phase -ceq 'Prepare') {
    Need ($PrNumber -eq $prScope -and $Head -cmatch '^[a-f0-9]{40}$' -and
          $RegressionRun -gt 0 -and $SourceRun -gt 0 -and
          $RehearsalRun -gt 0 -and $TerminalSeq -gt 9 -and
          $TerminalHash -cmatch '^[a-f0-9]{64}$' -and
          -not (Test-Path -LiteralPath $cert)) 'PREPARE_ARGS_OR_ALREADY_SPENT'
    $expected=$prepPrefix+$Target+' '+$Head+' '+$PrNumber+' '+$RegressionRun+' '+$SourceRun+' '+$RehearsalRun+' '+$TerminalSeq+' '+$TerminalHash
    Need ($event.comment.body -ceq $expected) 'PREPARE_COMMENT_FIELDS_DRIFT'
    $pr=Remote ('repos/'+$repo+'/pulls/'+$PrNumber)
    Need ($pr.state -ceq 'closed' -and $pr.merged -eq $true -and
          $pr.merge_commit_sha -ceq $Target -and $pr.head.sha -ceq $Head -and
          $pr.user.login -ceq 'spoonman136668-ai') 'MERGED_EXACT_OWNER_PR_REQUIRED'
    CheckCI $RegressionRun @('windows_f139','linux_f139','windows_genenv','linux_genenv','windows_native','linux_native','windows','linux') $Head
    CheckCI $SourceRun @('source (ubuntu-latest)','source (windows-latest)') $Head
    CheckCI $RehearsalRun @('development-rehearsal (ubuntu-latest)','development-rehearsal (windows-latest)') $Head

    Need ($task.Settings.Enabled -eq $true -and [string]$task.State -ceq 'Running' -and
          @(Owners).Count -eq 1) 'ONLY_RUNNING_ORIGINAL_OWNER_REQUIRED'
    $source=TaskArg $task 'RepositoryRoot'
    $oldStage=Join-Path $root ('release-candidates\'+$previousMain)
    Need ([IO.Path]::GetFullPath($source) -ieq [IO.Path]::GetFullPath($oldStage)) 'PREVIOUS_TASK_SOURCE_DRIFT'
    $oldCommit=Remote ('repos/'+$repo+'/git/commits/'+$previousMain)
    Need ($oldCommit.sha -ceq $previousMain) 'PREVIOUS_SOURCE_COMMIT_MISSING'
    ExactGit $source $previousMain ([string]$oldCommit.tree.sha)

    # Build the new content-addressed checkout first while old owner runs;
    # no rollback/reuse of an ambiguous or partially created staging path.
    $stage=Join-Path $root ('release-candidates\'+$Target)
    Need (-not(Test-Path -LiteralPath $stage) -and
          $null -eq (Get-Item -LiteralPath $stage -Force -ErrorAction SilentlyContinue)) 'NEW_STAGE_ALREADY_SPENT'
    & git clone --no-local --no-checkout --quiet -- $env:GITHUB_WORKSPACE $stage
    Need ($LASTEXITCODE -eq 0) 'STAGE_CLONE_FAILED'
    & git -C $stage checkout --quiet --detach $Target
    Need ($LASTEXITCODE -eq 0) 'STAGE_CHECKOUT_FAILED'
    & git -C $stage remote remove origin
    Need ($LASTEXITCODE -eq 0) 'STAGE_REMOVE_REMOTE_FAILED'
    ExactGit $stage $Target ([string]$commit.tree.sha)

    # STOP/DISABLE is separately owner-approved through this exact original
    # issue comment. Failure after this point leaves the SAME task disabled.
    Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
    for($i=0;$i -lt 80 -and @(Owners).Count -ne 0;$i++){Start-Sleep -Milliseconds 250}
    Need (@(Owners).Count -eq 0 -and
          (Get-ScheduledTask -TaskName $taskName).Settings.Enabled -eq $false) 'STOPPED_OWNER_CUSTODY_REQUIRED'

    # Exact original owner kernel lock + query-only SQLite cold evidence
    # verifies ALL historical worker ZIP receipts before signing the new cert.
    $request=[ordered]@{
      candidate=$Target; head=$Head; regression_run_id=[int64]$RegressionRun
      rehearsal_run_id=[int64]$RehearsalRun; source_run_id=[int64]$SourceRun
    }
    $encoded=Encoded ($request | ConvertTo-Json -Compress -Depth 6)
    $result=@(& $python -B -m f139.nci04_fresh_owner_source_forward_v2 preflight $db $encoded)
    Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1) 'COLD_V2_PREFLIGHT_FAILED'
    $snapshot=($result[0] | ConvertFrom-Json)
    Need ($snapshot.terminal_seq -eq $TerminalSeq -and
          $snapshot.terminal_hash -ceq $TerminalHash -and
          $snapshot.previous_owner_source_sha -ceq $previousMain -and
          $snapshot.owner_source_sha -ceq $Target) 'COLD_CHECKPOINT_SOURCE_OR_HISTORY_DRIFT'
    $unsigned=@{}
    foreach($prop in $snapshot.PSObject.Properties){$unsigned[$prop.Name]=$prop.Value}
    $unsigned['owner_run_id']=[int64]$env:GITHUB_RUN_ID
    $unsigned['owner_comment_id']=[int64]$event.comment.id
    $encodedDoc=Encoded ($unsigned | ConvertTo-Json -Compress -Depth 6)
    $signed=@(& $python -B -m f139.nci04_fresh_owner_source_forward_v2 sign-cert $cert $encodedDoc)
    Need ($LASTEXITCODE -eq 0 -and $signed.Count -eq 1 -and
          $signed[0] -ceq 'F139_FRESH_FORWARD_V2_SIGNED_CREATE_ONLY') 'CREATE_ONLY_SIGNED_CERT_FAILED'
    $arguments=[string]$task.Actions[0].Arguments
    Need ($arguments.Split(@($source),[StringSplitOptions]::None).Count -eq 3) 'PREVIOUS_TASK_SOURCE_PATH_NOT_UNIQUE'
    $newArguments=$arguments.Replace($source,$stage)
    Need ($newArguments -cne $arguments -and
          $newArguments.Contains($stage)) 'NEW_ACTION_SOURCE_NOT_UNIQUE'
    $newAction=New-ScheduledTaskAction -Execute ([string]$task.Actions[0].Execute) -Argument $newArguments
    Set-ScheduledTask -TaskName $taskName -Action $newAction -ErrorAction Stop | Out-Null
    $after=OwnerTask
    Need ($after.Settings.Enabled -eq $false -and
          [string]$after.Actions[0].Arguments -ceq $newArguments -and
          @(Owners).Count -eq 0) 'PREPARED_DISABLED_OWNER_INVARIANT'
    Write-Output 'F139_FRESH_OWNER_SOURCE_FORWARD_V2_PREPARED_DISABLED=PASS'
    Write-Output 'F139_WORKER_DISPATCHES=ZERO'
    Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
  } else {
    Need ($PrepRun -gt 0 -and
          $event.comment.body -ceq ($startPrefix+$Target+' '+$PrepRun)) 'START_COMMENT_OR_RUN_INVALID'
    $old=Get-Content -LiteralPath $cert -Raw -ErrorAction Stop | ConvertFrom-Json
    Need ($old.schema -ceq 'forge.f139.fresh-original-owner-source-forward.v2' -and
          $old.pr_number -eq $prScope -and
          $old.owner_run_id -eq $PrepRun -and
          $old.owner_source_sha -ceq $Target -and
          $old.owner_source_tree -ceq $commit.tree.sha) 'START_V2_SIGNED_SOURCE_MISMATCH'
    $prep=Remote ('repos/'+$repo+'/actions/runs/'+$PrepRun)
    $jobs=Remote ('repos/'+$repo+'/actions/runs/'+$PrepRun+'/jobs?per_page=100')
    Need ($prep.event -ceq 'issue_comment' -and
          $prep.head_sha -ceq $Target -and
          $prep.run_attempt -eq 1 -and
          $prep.status -ceq 'completed' -and $prep.conclusion -ceq 'success' -and
          @($jobs.jobs | Where-Object {$_.name -ceq 'fresh-original-owner-source-forward-v2-prepare' -and
            $_.runner_name -ceq 'FORGE-CODEX-REMOTE' -and $_.conclusion -ceq 'success'}).Count -eq 1) 'START_PREPARE_CUSTODY_NOT_ACCEPTED'
    Need ($task.Settings.Enabled -eq $false -and @(Owners).Count -eq 0) 'START_REQUIRES_DISABLED_ORIGINAL'
    $source=TaskArg $task 'RepositoryRoot'
    $stage=Join-Path $root ('release-candidates\'+$Target)
    Need ([IO.Path]::GetFullPath($source) -ieq [IO.Path]::GetFullPath($stage)) 'START_SOURCE_STAGE_DRIFT'
    ExactGit $stage $Target ([string]$commit.tree.sha)
    $request=[ordered]@{expected_source_sha=$Target}
    $encoded=Encoded ($request | ConvertTo-Json -Compress)
    $result=@(& $python -B -m f139.nci04_fresh_owner_source_forward_v2 verify-cert $db $encoded)
    Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1 -and
          $result[0] -ceq 'F139_FRESH_FORWARD_V2_OWNER_CUSTODY_VERIFIED') 'START_COLD_OWNER_CHAIN_INVALID'
    Enable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
    for($i=0;$i -lt 80 -and @(Owners).Count -ne 1;$i++){Start-Sleep -Milliseconds 250}
    Need (@(Owners).Count -eq 1 -and
          (Get-ScheduledTask -TaskName $taskName).Settings.Enabled -eq $true) 'START_SAME_ORIGINAL_TASK_NOT_RUNNING'
    Write-Output 'F139_FRESH_ORIGINAL_OWNER_SOURCE_FORWARD_V2_RUNNING=PASS'
    Write-Output 'F139_NO_NEW_CONTROLLER_OR_SCHEDULER=TRUE'
    Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
  }
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
}
