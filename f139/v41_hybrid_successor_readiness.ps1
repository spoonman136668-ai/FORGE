# Windows original-owner V41->Hybrid READINESS ONLY, NOT SOURCE COMMIT.
# Unregistered in Actions, no scheduled-task change, no SQLite writer.
param(
  [Parameter(Mandatory=$true)][string]$Target,
  [Parameter(Mandatory=$true)][long]$BackupRunId,
  [Parameter(Mandatory=$true)][string]$BackupManifest,
  [Parameter(Mandatory=$true)][long]$PairedApprovalId
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code) {
  if(-not $ok){throw ('F139_HYBRID_RELEASE_READINESS_'+$code)}
}
Need ($Target -cmatch '^[a-f0-9]{40}$' -and
  $BackupRunId -gt 0 -and $PairedApprovalId -gt 0 -and
  $BackupManifest -cmatch '^[a-f0-9]{64}$') 'TARGET_BOUND_FULL_BACKUP_REQUIRED'
Need ($env:GITHUB_REPOSITORY -ceq 'spoonman136668-ai/FORGE' -and
  $env:GITHUB_ACTOR -ceq 'spoonman136668-ai' -and
  $env:GITHUB_EVENT_NAME -ceq 'issue_comment' -and
  $env:GITHUB_REF -ceq 'refs/heads/main' -and
  $env:GITHUB_SHA -ceq $Target -and
  $env:GITHUB_RUN_ATTEMPT -ceq '1' -and
  $env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and
  -not $env:OPENAI_API_KEY) 'ORIGINAL_FIRST_ATTEMPT_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_EVENT_PATH -PathType Leaf) 'OWNER_EVENT_REQUIRED'
Need (Test-Path -LiteralPath $env:GITHUB_WORKSPACE -PathType Container) 'SOURCE_CHECKOUT_REQUIRED'
$rev=(& git -C $env:GITHUB_WORKSPACE rev-parse HEAD | Out-String).Trim()
Need ($LASTEXITCODE -eq 0 -and $rev -ceq $Target) 'EXACT_CHECKOUT_SHA_REQUIRED'
$dirty=@(& git -C $env:GITHUB_WORKSPACE status --porcelain --untracked-files=all)
Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'UNCLEAN_CHECKOUT_DENIED'
$env:PYTHONPATH=$env:GITHUB_WORKSPACE
& python -B -m f139.nci04_v41_hybrid_release_readiness --target $Target --backup-run-id $BackupRunId --backup-manifest $BackupManifest --paired-approval-id $PairedApprovalId
Need ($LASTEXITCODE -eq 0) 'READONLY_RELEASE_RECEIPT_NOT_QUALIFIED'
Write-Output 'F139_HYBRID_SOURCE_TRANSITION=FALSE'
Write-Output 'F139_HYBRID_TASK_POLICY_MUTATED=FALSE'
Write-Output 'F139_HYBRID_SCIENTIFIC_FIRST_USE=FALSE'
