# Unregistered V41->Hybrid original Windows source-only COMMIT-and-HOLD.
# Requires a newly authenticated OWNER issue comment and previously sealed
# target-bound complete backup. NO automatic task control or policy activation.
param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Need([bool]$ok,[string]$why) {
  if(-not $ok){throw ('F139_HYBRID_V41_SOURCE_COMMIT_'+$why)}
}
Need ($Target -cmatch '^[0-9a-f]{40}$' -and
  $env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'WRONG_ORIGINAL_FIRST_ATTEMPT'
Need (Test-Path -LiteralPath $env:GITHUB_EVENT_PATH -PathType Leaf) 'NO_OWNER_EVENT'
Need (Test-Path -LiteralPath $env:GITHUB_WORKSPACE -PathType Container) 'NO_SOURCE_CHECKOUT'
$event=Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw|ConvertFrom-Json
Need ($event.action -ceq 'created' -and
  $event.issue.number -eq 807 -and
  $event.issue.user.login -ceq 'spoonman136668-ai' -and
  $null -eq $event.issue.PSObject.Properties['pull_request'] -and
  $event.sender.login -ceq 'spoonman136668-ai' -and
  $event.comment.user.login -ceq 'spoonman136668-ai' -and
  $event.comment.author_association -ceq 'OWNER' -and
  [string]$event.comment.body -clike 'F139-HYBRID-V41-SOURCE-COMMIT *') 'EXACT_NEW_OWNER_COMMIT_COMMENT_REQUIRED'
$sha=(& git -C $env:GITHUB_WORKSPACE rev-parse HEAD|Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $sha -ceq $Target) 'PROTECTED_MAIN_SHA_DRIFT'
$dirty=@(& git -C $env:GITHUB_WORKSPACE status --porcelain --untracked-files=all)
Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'SOURCE_CHECKOUT_DIRTY'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($who)
Need ($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'OWNER_ADMIN_REQUIRED'
$task=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
} catch {}
Need ($task.Settings.Enabled -eq $false -and
  [string]$task.State -ceq 'Disabled' -and
  @($task.Actions).Count -eq 1 -and @($task.Triggers).Count -eq 3 -and
  ([string]$task.Principal.UserId -ieq $who.Name -or
    $sid -ceq $who.User.Value)) 'ORIGINAL_OWNER_TASK_MUST_ALREADY_BE_DISABLED'
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
try {
  & python -B -m f139.nci04_v41_hybrid_original_commit --target $Target
  Need ($LASTEXITCODE -eq 0) 'ORIGINAL_SOURCE_COMMIT_OR_HOLD_UNVERIFIED'
  $after=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
  Need ($after.Settings.Enabled -eq $false -and
    [string]$after.State -ceq 'Disabled') 'POSTCOMMIT_TASK_NOT_DISABLED'
  Write-Output 'F139_HYBRID_V41_ORIGINAL_SOURCE_COMMIT_HOLD=PASS'
  Write-Output 'F139_HYBRID_OWNER_TASK_RESUME=FALSE'
  Write-Output 'F139_HYBRID_POLICY_UPDATE=FALSE'
  Write-Output 'F139_HYBRID_SCIENTIFIC_FIRST_USE=FALSE'
} catch {
  # On an uncertain commit, NEVER restore old SQLite or resume V41:
  # independently authenticated forward repair is mandatory.
  throw ('F139_HYBRID_V41_ORIGINAL_SOURCE_FORWARD_REPAIR_HOLD: '+
         $_.Exception.Message)
}
