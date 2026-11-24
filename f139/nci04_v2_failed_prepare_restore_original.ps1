# One narrowly authenticated recovery of the SAME disabled original V1 owner.
# V2 PREPARE #45091947666 failed AFTER disabling the task. Never replay it.
# No new controller, scheduler, PR/issue, POST, worker or scientific first-use.
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Target,
  [Parameter(Mandatory)][int64]$FailedRun,
  [Parameter(Mandatory)][int64]$TerminalSeq,
  [Parameter(Mandatory)][string]$TerminalHash
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='spoonman136668-ai/FORGE'
$previousMain='852b473bf714038c75254650503c279768eff8cf'
# Bind the merge to the merged PR identity instead of self-referential SHAs.
# All remote GETs must succeed before the original scheduled task is touched.
$original='f24251e0d95938e593a54c1577a34efadc8080d8'
$originalTree='b63e6346b9d665664bb4e248535a60db9473b592'
$failed=45091947666L
$audit=45092273168L
$originalName='FORGE-F139-UnifiedController'
$dbHead='b4e2229ce9c8dba9a430c37277bb8630c5d6f6014e429d9b62724130c7f82da1'
$root=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$db=Join-Path $root 'f139-fresh-dev-44831323193\state.sqlite'
$certDir=Split-Path $db -Parent
$prefix='F139-V2-FAILED-PREPARE-RESTORE-ORIGINAL '
function Need([bool]$ok,[string]$reason) {
  if(-not $ok){ throw ('F139_V2_RESTORE_'+$reason) }
}
function Remote([string]$path) {
  Need ($path.StartsWith('repos/spoonman136668-ai/FORGE/',[StringComparison]::Ordinal) -and
        -not $path.Contains('..')) 'UNSCOPED_GET'
  $rows=@(& gh api $path 2>$null)
  Need ($LASTEXITCODE -eq 0 -and $rows.Count -gt 0) 'READONLY_PROVIDER_GET_FAILED'
  return (($rows -join [Environment]::NewLine) | ConvertFrom-Json)
}
function Field($task,[string]$key) {
  $m=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  Need $m.Success ('MISSING_ORIGINAL_'+$key)
  return [string]$m.Groups[1].Value
}
function Controllers {
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
}
function ExactCheckout([string]$path,[string]$source,[string]$tree,[bool]$allowRemote) {
  Need (Test-Path -LiteralPath $path -PathType Container) 'ORIGINAL_SOURCE_MISSING'
  $actual=(& git -C $path rev-parse HEAD | Out-String).Trim()
  $actualTree=(& git -C $path rev-parse 'HEAD^{tree}' | Out-String).Trim()
  $dirty=@(& git -C $path status --porcelain --untracked-files=all)
  $remotes=(& git -C $path remote | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $actual -ceq $source -and
        $actualTree -ceq $tree -and $dirty.Count -eq 0 -and
        ($allowRemote -or -not $remotes)) 'ORIGINAL_SHA_TREE_OR_DIRTY'
}
# Validate owner and immutable event BEFORE touching original task.
Need ($Target -cmatch '^[a-f0-9]{40}$' -and $Target -ceq $env:GITHUB_SHA -and
      $FailedRun -eq $failed -and $TerminalSeq -eq 23 -and
      $TerminalHash -ceq $dbHead -and
      $env:GITHUB_REPOSITORY -ceq $repo -and
      $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
      $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
      $env:GITHUB_REF -ceq 'refs/heads/main' -and
      $env:GITHUB_WORKFLOW_REF -ceq ($repo+'/.github/workflows/f139-v2-failed-prepare-original-restore.yml@refs/heads/main') -and
      $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
      $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
      $env:GH_TOKEN -and
      -not $env:OPENAI_API_KEY -and -not $env:CLOUDFLARE_API_TOKEN) 'OWNER_RUNNER_AND_SOURCE_REQUIRED'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
Need ([Security.Principal.WindowsPrincipal]::new($who).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)) 'ORIGINAL_ADMIN_REQUIRED'
$evt=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
$expected=$prefix+$Target+' '+$FailedRun+' '+$TerminalSeq+' '+$TerminalHash
Need ($evt.action -ceq 'created' -and $evt.issue.number -eq 1830 -and
      $evt.issue.state -ceq 'open' -and
      $evt.issue.user.login -ceq 'spoonman136668-ai' -and
      $evt.sender.login -ceq 'spoonman136668-ai' -and
      $evt.comment.user.login -ceq 'spoonman136668-ai' -and
      $evt.comment.author_association -ceq 'OWNER' -and
      [int64]$evt.comment.id -gt 7088786924 -and
      $null -eq $evt.issue.PSObject.Properties['pull_request'] -and
      [string]$evt.comment.body -ceq $expected) 'UNIQUE_ORIGINAL_OWNER_COMMENT_REQUIRED'
$c=Remote ('repos/'+$repo+'/issues/comments/'+$evt.comment.id)
Need ([int64]$c.id -eq [int64]$evt.comment.id -and
      $c.user.login -ceq 'spoonman136668-ai' -and
      $c.author_association -ceq 'OWNER' -and
      $c.body -ceq $expected -and
      $c.created_at -ceq $evt.comment.created_at) 'OWNER_COMMENT_PROVIDER_DRIFT'
$main=Remote ('repos/'+$repo+'/branches/main')
$commit=Remote ('repos/'+$repo+'/git/commits/'+$Target)
$recoveryPr=Remote ('repos/'+$repo+'/pulls/1870')
$recoveryMergeSha=[string]$recoveryPr.merge_commit_sha
$recoveryMerge=Remote ('repos/'+$repo+'/git/commits/'+$recoveryMergeSha)
Need ($main.protected -eq $true -and $main.commit.sha -ceq $Target -and
      $commit.sha -ceq $Target -and
      $recoveryMerge.sha -ceq $recoveryMergeSha -and
      @($recoveryMerge.parents).Count -eq 2 -and
      $recoveryMerge.parents[0].sha -ceq $previousMain -and
      $recoveryPr.number -eq 1870 -and $recoveryPr.merged -eq $true -and
      $recoveryPr.state -ceq 'closed' -and
      $recoveryPr.user.login -ceq 'spoonman136668-ai' -and
      $recoveryPr.head.ref -ceq 'engineering/f139-v2-postfail-original-v1-recovery-20261122' -and
      $recoveryPr.head.repo.full_name -ceq $repo -and
      $recoveryPr.base.ref -ceq 'main' -and
      $recoveryPr.base.repo.full_name -ceq $repo -and
      $recoveryPr.base.sha -ceq $previousMain -and
      $recoveryPr.merge_commit_sha -ceq $recoveryMergeSha -and
      $recoveryPr.head.sha -ceq $recoveryMerge.parents[1].sha) 'EXACT_RECOVERY_MERGE_REQUIRED'
$prSource=Remote ('repos/'+$repo+'/git/commits/'+$recoveryPr.head.sha)
Need ($prSource.sha -ceq $recoveryPr.head.sha -and
      $recoveryMerge.tree.sha -ceq $prSource.tree.sha) 'RECOVERY_MERGE_TREE_DIFFERS_FROM_QUALIFIED_PR'
# Later protected-main merges are allowed only when the original recovery merge
# remains an ancestor and the exact executable recovery files are unchanged.
& git -C $env:GITHUB_WORKSPACE merge-base --is-ancestor $recoveryMergeSha $Target
Need ($LASTEXITCODE -eq 0) 'RECOVERY_MERGE_NOT_ANCESTOR_OF_CURRENT_MAIN'
# Original recovery workflow and non-test Python runtime sources remain pinned
# to the exact qualified PR #1870 merge. Later tests and unrelated workflows may evolve.
$workflowPath='.github/workflows/f139-v2-failed-prepare-original-restore.yml'
$workflowMergeBlob=(& git -C $env:GITHUB_WORKSPACE rev-parse ($recoveryMergeSha+':'+$workflowPath) | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $workflowMergeBlob.Length -eq 40) 'RECOVERY_WORKFLOW_MERGE_BLOB_UNAVAILABLE'
$workflowMainBlob=(& git -C $env:GITHUB_WORKSPACE rev-parse ($Target+':'+$workflowPath) | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $workflowMainBlob -ceq $workflowMergeBlob) 'RECOVERY_WORKFLOW_SOURCE_DRIFT'
$recoveryPythonFiles=@(& git -C $env:GITHUB_WORKSPACE ls-tree -r --name-only $recoveryMergeSha -- f139)
Need ($LASTEXITCODE -eq 0 -and $recoveryPythonFiles.Count -gt 0) 'RECOVERY_DEPENDENCY_TREE_UNAVAILABLE'
$recoveryPythonFiles=@($recoveryPythonFiles | Where-Object { $_ -like 'f139/*.py' -and $_ -notlike 'f139/test_*.py' })
Need ($recoveryPythonFiles.Count -gt 0) 'RECOVERY_DEPENDENCY_PYTHON_TREE_EMPTY'
foreach($path in $recoveryPythonFiles){
  $mergeBlob=(& git -C $env:GITHUB_WORKSPACE rev-parse ($recoveryMergeSha+':'+$path) | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $mergeBlob.Length -eq 40) 'RECOVERY_DEPENDENCY_MERGE_BLOB_UNAVAILABLE'
  $mainBlob=(& git -C $env:GITHUB_WORKSPACE rev-parse ($Target+':'+$path) | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0 -and $mainBlob -ceq $mergeBlob) 'RECOVERY_DEPENDENCY_SOURCE_DRIFT'
}

# The workflow checks out exact protected main at $Target. Bind the running
# PowerShell file to that commit's own blob rather than pinning it to an older
# recovery PR (which would reject every legitimate follow-up source correction).
$scriptPath='f139/nci04_v2_failed_prepare_restore_original.ps1'
$currentScriptBlob=(& git -C $env:GITHUB_WORKSPACE rev-parse ($Target+':'+$scriptPath) | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $currentScriptBlob.Length -eq 40) 'RECOVERY_SCRIPT_MAIN_BLOB_UNAVAILABLE'
$runningScriptBlob=(& git -C $env:GITHUB_WORKSPACE hash-object $PSCommandPath | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $runningScriptBlob.Length -eq 40 -and
      $runningScriptBlob -ceq $currentScriptBlob) 'RECOVERY_SCRIPT_CHECKOUT_DRIFT'
ExactCheckout $env:GITHUB_WORKSPACE $Target ([string]$commit.tree.sha) $true
# ACTION_RUNS /jobs GET was the failing endpoint in the consumed PREPARE.
# Do not re-depend on it for original-owner recovery. Confirm the two exact
# immutable run IDs, actors, source SHAs and workflow identities. Current task,
# signed V1 certificate and entire cold SQLite chain are checked independently.
$failure=Remote ('repos/'+$repo+'/actions/runs/'+$FailedRun)
Need ($failure.id -eq $FailedRun -and
      $failure.name -ceq 'FORGE F139 V2 original-owner source forward (same task, owner-only)' -and
      $failure.path -ceq '.github/workflows/f139-fresh-owner-source-forward-v2.yml' -and
      $failure.event -ceq 'issue_comment' -and
      $failure.actor.login -ceq 'spoonman136668-ai' -and
      $failure.head_sha -ceq $previousMain -and
      $failure.run_attempt -eq 1 -and $failure.status -ceq 'completed' -and
      $failure.conclusion -ceq 'failure') 'FAILED_PREPARE_IDENTITY_NOT_VERIFIED'
$prior=Remote ('repos/'+$repo+'/actions/runs/'+$audit)
Need ($prior.id -eq $audit -and
      $prior.name -ceq 'FORGE F139 original-host bounded read-only block codes (one PR)' -and
      $prior.path -ceq '.github/workflows/f139-original-host-block-codes-one-pr.yml' -and
      $prior.head_sha -ceq 'ab87431e8718eec1e160b0bfbd077ee6550a3844' -and
      $prior.actor.login -ceq 'spoonman136668-ai' -and
      $prior.run_attempt -eq 1 -and $prior.event -ceq 'pull_request' -and
      $prior.status -ceq 'completed' -and
      $prior.conclusion -ceq 'success') 'ORIGINAL_OWNER_AUDIT_PROVENANCE'
$task=Get-ScheduledTask -TaskName $originalName -ErrorAction Stop
$sid=''
try {$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value} catch {}
$taskActionsCount=@($task.Actions).Count
$taskTriggersCount=@($task.Triggers).Count
$taskPrincipalMatch=([string]$task.Principal.UserId -ieq $who.Name -or $sid -ceq $who.User.Value)
$taskExecuteMatch=($taskActionsCount -ge 1 -and [IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ieq 'powershell.exe')
$taskEnabled=[bool]$task.Settings.Enabled
$taskState=[string]$task.State
$controllerCount=@(Controllers).Count
Write-Output ('F139_V2_RESTORE_PRECHECK='+(ConvertTo-Json @{
  actions_count=$taskActionsCount
  triggers_count=$taskTriggersCount
  principal_match=$taskPrincipalMatch
  execute_match=$taskExecuteMatch
  enabled=$taskEnabled
  state=$taskState
  controller_count=$controllerCount
} -Compress))
Need ($taskActionsCount -eq 1 -and $taskTriggersCount -eq 3 -and
      $taskPrincipalMatch -and $taskExecuteMatch -and
      $taskEnabled -eq $false -and
      $taskState -ceq 'Disabled' -and $controllerCount -eq 0) 'EXACT_DISABLED_ORIGINAL_OWNER_REQUIRED'
$source=Field $task 'RepositoryRoot'
$database=Field $task 'Database'
$python=Field $task 'PythonExe'
$wrapper=Field $task 'File'
$keyfile=Field $task 'EncryptedKeyFile'
Need ([IO.Path]::GetFullPath($source) -ieq [IO.Path]::GetFullPath(
         (Join-Path $root ('release-candidates\'+$original))) -and
      [IO.Path]::GetFullPath($database) -ieq [IO.Path]::GetFullPath($db) -and
      [IO.Path]::GetFileName($wrapper) -ceq 'Run-FORGE-F139.ps1' -and
      (Test-Path -LiteralPath $python -PathType Leaf) -and
      (Test-Path -LiteralPath $keyfile -PathType Leaf) -and
      (Test-Path -LiteralPath $db -PathType Leaf)) 'ORIGINAL_RELEASE_PATH_OR_FILE_DRIFT'
ExactCheckout $source $original $originalTree $false
$secure=Import-Clixml -LiteralPath $keyfile
Need ($secure -is [Security.SecureString]) 'ORIGINAL_DPAPI_CUSTODY_DRIFT'
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {$env:F139_WORKER_HMAC_KEY=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}
finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
Need ($env:F139_WORKER_HMAC_KEY.Length -ge 32) 'ORIGINAL_KEY_INVALID'
try {
  $env:PYTHONPATH=$env:GITHUB_WORKSPACE
  $env:PYTHONDONTWRITEBYTECODE='1'
  $result=@(& $python -B -m f139.nci04_v2_failed_prepare_restore_original audit $db $certDir ([string]$TerminalSeq) $TerminalHash)
  Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1 -and
        [string]$result[0] -clike 'F139_V2_POSTFAIL_COLD=*') 'COLD_SIGNED_V1_CUSTODY_REJECTED'
  $report=([string]$result[0]).Substring('F139_V2_POSTFAIL_COLD='.Length) | ConvertFrom-Json
  Need ($report.head_seq -eq 23 -and $report.head_hash -ceq $dbHead -and
        $report.verified_tasks -eq 3 -and
        $report.original_source_sha -ceq $original -and
        $report.v2_certificate_present -eq $false -and
        $report.sqlite_mutations -eq 0 -and $report.worker_dispatches -eq 0) 'COLD_V1_READBACK_DRIFT'
  # All reads, signatures and process checks have succeeded. Single reversible
  # owner-approved mutation: enable and start the existing original task.
  Need (@(Controllers).Count -eq 0 -and
        (Get-ScheduledTask -TaskName $originalName).Settings.Enabled -eq $false) 'OWNER_MOVED_BEFORE_RESTORE'
  # If startup or its immediate identity check fails, return the same task
  # to the disabled state. Never replay PREPARE or spawn another controller.
  try {
    Enable-ScheduledTask -TaskName $originalName -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $originalName -ErrorAction Stop
    for($i=0;$i -lt 80 -and @(Controllers).Count -ne 1;$i++){Start-Sleep -Milliseconds 250}
    $after=Get-ScheduledTask -TaskName $originalName -ErrorAction Stop
    $observed=@(Controllers)
    $matched=@($observed | Where-Object {
      [string]$_.CommandLine -and
      ([string]$_.CommandLine).IndexOf($db,[StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    Need ($after.Settings.Enabled -eq $true -and
          $observed.Count -eq 1 -and $matched.Count -eq 1 -and
          [string]$after.Actions[0].Arguments -ceq [string]$task.Actions[0].Arguments) 'SAME_OWNER_NOT_STARTED'
  } catch {
    $startupFailure=$_
    # Disabling a task does not terminate a running instance. Attempt both
    # actions; if either cannot be proved safe, report a recovery failure.
    $disableFailed=$false
    try { Disable-ScheduledTask -TaskName $originalName -ErrorAction Stop | Out-Null }
    catch { $disableFailed=$true }
    try { Stop-ScheduledTask -TaskName $originalName -ErrorAction Stop | Out-Null }
    catch {
      # Stop can fail when START failed before any task instance existed.
      # Verify the process census rather than assuming an error is harmless.
    }
    for($i=0;$i -lt 40 -and @(Controllers).Count -ne 0;$i++){
      Start-Sleep -Milliseconds 250
    }
    $rollback=Get-ScheduledTask -TaskName $originalName -ErrorAction Stop
    Need (-not $disableFailed -and
          $rollback.Settings.Enabled -eq $false -and
          [string]$rollback.State -ceq 'Disabled' -and
          @(Controllers).Count -eq 0) 'FAILED_START_ROLLBACK_UNVERIFIED'
    throw $startupFailure
  }
  Write-Output 'F139_V2_FAILED_PREPARE_ORIGINAL_V1_SAME_TASK_RESTORED=PASS'
  Write-Output 'F139_NEW_CONTROLLER_OR_SCHEDULER=FALSE'
  Write-Output 'F139_WORKER_DISPATCH_AUTHORIZED=FALSE'
  Write-Output 'F139_SCIENTIFIC_FIRST_USE=FALSE'
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
}
