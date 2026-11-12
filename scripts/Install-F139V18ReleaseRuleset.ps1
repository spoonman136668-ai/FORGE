# F139 V18 release-ref protection. Read-only by default.
# Run only from a clean, qualified governance checkout, never from the live owner.
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = 'spoonman136668-ai/FORGE'
$oldMain = '3775bed30891ff748197a539afe5b92813680e26'
$target = '5a040dd4dd8c4a3203c7e4d751a0cf01065717ad'
$ruleName = 'FORGE F139 immutable owner release refs'
$rulePattern = 'refs/heads/f139-owner-release-*'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$policyFile = Join-Path $root 'reference/governance/f139-owner-release-ref-ruleset-proposal.json'
function Deny([string]$reason) { throw "F139_V18_ADMIN_LOCK_DENIED_$reason" }
function Api([string]$path) {
    $raw = & gh api "repos/$repo/$path"
    if($LASTEXITCODE -ne 0) { Deny 'GITHUB_READ_FAILED' }
    return ($raw | ConvertFrom-Json -Depth 40)
}
if(-not (Get-Command gh -ErrorAction SilentlyContinue) -or
   -not (Get-Command go -ErrorAction SilentlyContinue) -or
   -not (Get-Command git -ErrorAction SilentlyContinue)) {
    Deny 'GIT_GH_GO_REQUIRED'
}
if(-not (Test-Path -LiteralPath $policyFile -PathType Leaf)) {
    Deny 'REVIEWED_RULESET_FILE_MISSING'
}
$branch = (& git -C $root branch --show-current | Out-String).Trim()
$head = (& git -C $root rev-parse HEAD | Out-String).Trim()
$dirty = (& git -C $root status --porcelain --untracked-files=all | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or
   $branch -cne 'governance/f139-release-ref-protection-20261028' -or
   $head -cnotmatch '^[a-f0-9]{40}$' -or $dirty.Length -ne 0) {
    Deny 'CLEAN_GOVERNANCE_CHECKOUT_REQUIRED'
}
Push-Location $root
try {
    & go test ./branchpolicy -run 'TestF139OwnerReleaseRuleset' -count=1
    if($LASTEXITCODE -ne 0) { Deny 'RULESET_NEGATIVE_TESTS_NOT_PASSING' }
} finally { Pop-Location }
$plan = Get-Content -LiteralPath $policyFile -Raw | ConvertFrom-Json -Depth 40
if($plan.name -cne $ruleName -or $plan.target -cne 'branch' -or
   $plan.enforcement -cne 'active' -or
   @($plan.bypass_actors).Count -ne 0 -or
   @($plan.conditions.ref_name.include).Count -ne 1 -or
   [string]$plan.conditions.ref_name.include[0] -cne $rulePattern -or
   @($plan.conditions.ref_name.exclude).Count -ne 0) {
    Deny 'PROPOSAL_SCOPE_DRIFT'
}
$types = @($plan.rules | ForEach-Object { [string]$_.type } | Sort-Object)
if($types.Count -ne 2 -or $types[0] -cne 'deletion' -or
   $types[1] -cne 'update') { Deny 'PROPOSAL_LOCK_DRIFT' }

$main = Api 'branches/main'
$release = Api "branches/f139-owner-release-$target"
$policy = Api 'issues/807'
$ownerPolicy = ([string]$policy.body | ConvertFrom-Json -Depth 40)
if($main.commit.sha -cne $oldMain -or $main.protected -ne $true -or
   $release.commit.sha -cne $target -or
   $ownerPolicy.source_sha -cne $oldMain -or $ownerPolicy.enabled -ne $true -or
   $ownerPolicy.scientific_first_use -ne $false -or
   $ownerPolicy.paid_model_calls -ne 0) {
    Deny 'ORIGINAL_MAIN_RELEASE_OR_OWNER_POLICY_DRIFT'
}
$all = @(Api 'rulesets')
$mainRules = @($all | Where-Object {$_.id -eq 25031517 -and
                $_.name -ceq 'FORGE main qualified-source only' -and
                $_.enforcement -ceq 'active'})
$releaseRules = @($all | Where-Object { $_.name -ceq $ruleName })
if($mainRules.Count -ne 1 -or $releaseRules.Count -gt 1) {
    Deny 'RULESET_INVENTORY_UNEXPECTED'
}
if($releaseRules.Count -eq 0) {
    if(-not $Apply) {
        Write-Host 'F139_V18_ADMIN_LOCK=NOT_INSTALLED_READONLY'
        Write-Host 'F139_V18_MAIN_AND_POLICY_UNCHANGED=TRUE'
        return
    }
    # Single bounded admin operation. Uses existing authenticated gh CLI;
    # no PAT, secret, permission grant, workflow dispatch or task mutation.
    $created = & gh api --method POST "repos/$repo/rulesets" --input $policyFile
    if($LASTEXITCODE -ne 0) { Deny 'ADMIN_WRITE_REJECTED' }
    $createdObject = $created | ConvertFrom-Json -Depth 40
    if([int64]$createdObject.id -le 0) { Deny 'CREATION_RECEIPT_INVALID' }
}
# Confirm server-side settings, not the proposed JSON or POST success alone.
$after = @(Api 'rulesets')
$matching = @($after | Where-Object {$_.name -ceq $ruleName})
if($matching.Count -ne 1 -or $matching[0].enforcement -cne 'active') {
    Deny 'ACTIVE_RULESET_NOT_UNIQUE'
}
$detail = Api "rulesets/$($matching[0].id)"
$lock = @($detail.rules | ForEach-Object {[string]$_.type} | Sort-Object)
if($detail.name -cne $ruleName -or $detail.target -cne 'branch' -or
   $detail.enforcement -cne 'active' -or
   @($detail.bypass_actors).Count -ne 0 -or
   @($detail.conditions.ref_name.include).Count -ne 1 -or
   [string]$detail.conditions.ref_name.include[0] -cne $rulePattern -or
   @($detail.conditions.ref_name.exclude).Count -ne 0 -or
   $lock.Count -ne 2 -or $lock[0] -cne 'deletion' -or $lock[1] -cne 'update') {
    Deny 'SERVER_ENFORCEMENT_OR_BYPASS_DRIFT'
}
$releaseAgain = Api "branches/f139-owner-release-$target"
$mainAgain = Api 'branches/main'
if($releaseAgain.commit.sha -cne $target -or $releaseAgain.protected -ne $true -or
   $mainAgain.commit.sha -cne $oldMain -or $mainAgain.protected -ne $true) {
    Deny 'RELEASE_BRANCH_NOT_PROTECTED_OR_MAIN_DRIFT'
}
Write-Host 'F139_V18_ADMIN_RULESET_ACTIVE_NO_BYPASS_UPDATE_DELETE=PASS'
Write-Host ('F139_V18_RULESET_ID=' + $matching[0].id)
Write-Host 'F139_V18_PR_HEAD_RELEASE_REF_PROTECTED=PASS'
Write-Host 'F139_V18_OWNER_CUTOVER_AUTHORIZED=FALSE'
Write-Host 'F139_V18_SCIENTIFIC_FIRST_USE=FALSE'
