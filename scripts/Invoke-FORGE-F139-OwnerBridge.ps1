# F139 owner-only GitHub Actions bridge. NEVER run this on GitHub-hosted runners.
# No automatic approval, source promotion, queue manipulation or dispatch.
[CmdletBinding()]
param(
  [ValidateSet('preflight','custody','transition','activate')]
  [string]$Phase = 'preflight',
  [Parameter(Mandatory)][string]$ExpectedMainSha,
  [Parameter(Mandatory)][string]$ExpectedHeadSha,
  [string]$ApprovalSha256 = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
  throw 'F139_OWNER_BRIDGE_REQUIRES_WINDOWS'
}
if ($env:GITHUB_ACTIONS -cne 'true' -or $env:GITHUB_EVENT_NAME -cne 'workflow_dispatch' -or
    $env:GITHUB_REF -cne 'refs/heads/main') {
  throw 'F139_OWNER_BRIDGE_MANUAL_MAIN_ONLY'
}
if ($ExpectedMainSha -cnotmatch '^[a-f0-9]{40}$' -or
    $ExpectedHeadSha -cnotmatch '^[a-f0-9]{64}$') {
  throw 'F139_OWNER_BRIDGE_IDENTITY_INVALID'
}
if ($env:GITHUB_SHA -cne $ExpectedMainSha) {
  throw 'F139_OWNER_BRIDGE_GITHUB_EVENT_SOURCE_DRIFT'
}
# A GitHub-hosted runner cannot decrypt this owner's DPAPI custody.
# These checks also reject SYSTEM, runner-service, or another user's SID.
$ownerRoot = $env:FORGE_F139_OWNER_ROOT
if ([string]::IsNullOrWhiteSpace($ownerRoot)) { throw 'F139_OWNER_ROOT_NOT_CONFIGURED' }
$root = [IO.Path]::GetFullPath($ownerRoot)
$python = (Get-Command python -ErrorAction Stop).Source
$git = (Get-Command git -ErrorAction Stop).Source
$gh = (Get-Command gh -ErrorAction Stop).Source
$db = Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite'
$key = Join-Path $env:LOCALAPPDATA 'FORGE-F139\worker-hmac.dpapi.xml'
$approvalDir = Join-Path $env:LOCALAPPDATA 'FORGE-F139\owner-cutover'
if (-not (Test-Path -LiteralPath $db -PathType Leaf)) { throw 'F139_OWNER_SQLITE_MISSING' }
if (-not (Test-Path -LiteralPath (Join-Path $root 'f139\local_controller.py') -PathType Leaf)) {
  throw 'F139_OWNER_SOURCE_CHECKOUT_MISSING'
}
$task = Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$ownerSID = (New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).Translate(
  [Security.Principal.SecurityIdentifier]).Value
if ($identity.User.Value -cne $ownerSID) { throw 'F139_OWNER_RUNNER_SID_MISMATCH' }
if ($task.State -ne 'Disabled') { throw 'F139_OWNER_TASK_MUST_BE_DISABLED' }
if (@($task.Actions).Count -ne 1) { throw 'F139_OWNER_TASK_ACTION_DRIFT' }
$rawArgs = [string]$task.Actions[0].Arguments
$rootMatch = [regex]::Match($rawArgs,'(?i)(?:^|\s)-RepositoryRoot\s+"([^"]+)"')
$dbMatch = [regex]::Match($rawArgs,'(?i)(?:^|\s)-Database\s+"([^"]+)"')
if (-not ($rootMatch.Success -and $dbMatch.Success) -or
    [IO.Path]::GetFullPath($rootMatch.Groups[1].Value) -ine $root -or
    [IO.Path]::GetFullPath($dbMatch.Groups[1].Value) -ine [IO.Path]::GetFullPath($db)) {
  throw 'F139_OWNER_SCHEDULED_SOURCE_OR_DB_DRIFT'
}
$protected = & $gh api 'repos/spoonman136668-ai/FORGE/branches/main' --jq '.protected'
if ($LASTEXITCODE -ne 0 -or $protected.Trim() -cne 'true') {
  throw 'F139_PROTECTED_MAIN_NOT_CONFIRMED'
}
$remoteSha = & $gh api 'repos/spoonman136668-ai/FORGE/branches/main' --jq '.commit.sha'
if ($LASTEXITCODE -ne 0 -or $remoteSha.Trim() -cne $ExpectedMainSha) {
  throw 'F139_PROTECTED_MAIN_SOURCE_DRIFT'
}
$head = & $git -C $root rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $head.Trim() -cne $ExpectedMainSha) {
  throw 'F139_OWNER_CHECKOUT_NOT_PROMOTED_EXACT_MAIN'
}
$dirty = & $git -C $root status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or @($dirty).Count -ne 0) {
  throw 'F139_OWNER_CHECKOUT_NOT_CLEAN'
}
# SQLite URI read-only with query_only. Do not invoke an initializing controller.
$reader = @'
import json, sqlite3, sys, pathlib
path = pathlib.Path(sys.argv[1]).resolve()
con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
try:
    con.execute("PRAGMA query_only=ON")
    m = con.execute("SELECT source_sha,head_seq,head_hash,enabled,legacy_suspended FROM meta WHERE id=1").fetchone()
    rows = con.execute("SELECT ticket,stage FROM tasks ORDER BY ticket").fetchall()
    print(json.dumps({"source_sha":m[0],"head_seq":m[1],"head_hash":m[2],
      "enabled":m[3],"legacy_suspended":m[4],
      "unverified":[list(x) for x in rows if x[1]!="VERIFIED"]},sort_keys=True))
finally:
    con.close()
'@
$stateText = $reader | & $python -B -c 'exec(__import__("sys").stdin.read())' $db
if ($LASTEXITCODE -ne 0) { throw 'F139_OWNER_SQLITE_READONLY_PREFLIGHT_FAILED' }
$state = $stateText | ConvertFrom-Json
if ($state.head_hash -cne $ExpectedHeadSha -or $state.enabled -ne 1 -or
    $state.legacy_suspended -ne 1 -or $state.source_sha -cnotmatch '^[a-f0-9]{40}$') {
  throw 'F139_OWNER_LEDGER_DRIFT'
}
$expectedNegatives = @(
  'f139-nci04-i696-5662e3586bc9-7bb8f27f',
  'f139-nci04-i706-09f3d7447900-09dc99f4'
)
if (@($state.unverified).Count -ne 2) { throw 'F139_OWNER_HISTORICAL_TASK_SET_DRIFT' }
foreach ($item in $state.unverified) {
  if ($item[1] -cne 'QUARANTINED' -or $expectedNegatives -cnotcontains $item[0]) {
    throw 'F139_OWNER_UNCERTIFIED_TASK_PRESENT'
  }
}
# Preflight is intentionally read-only and does not generate authorization.
if ($Phase -ceq 'preflight') {
  Write-Host 'F139_OWNER_BRIDGE_PREFLIGHT=PASS'
  Write-Host "F139_OWNER_BRIDGE_LEDGER_SEQ=$($state.head_seq)"
  Write-Host 'F139_OWNER_BRIDGE_MUTATIONS=ZERO'
  return
}
# Two independent prerequisites: a protected-environment manual action AND an
# operator-authored exact-head local approval file. No approval is constructed here.
if ($ApprovalSha256 -cnotmatch '^[a-f0-9]{64}$') {
  throw 'F139_OWNER_BRIDGE_APPROVAL_SHA_MISSING'
}
$gatePath = Join-Path $approvalDir ('A8E2A4-' + $Phase + '.json')
if (-not (Test-Path -LiteralPath $gatePath -PathType Leaf)) {
  throw 'F139_OWNER_BRIDGE_LOCAL_APPROVAL_MISSING'
}
if ((Get-FileHash -LiteralPath $gatePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne
    $ApprovalSha256) { throw 'F139_OWNER_BRIDGE_APPROVAL_HASH_DRIFT' }
$gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
$names = @($gate.PSObject.Properties.Name | Sort-Object)
$wanted = @('approved','expected_event_head_sha256','phase','qualified_main_sha','schema')
if (@(Compare-Object $names $wanted).Count -ne 0 -or
    $gate.schema -cne 'forge.f139.original-owner-bridge-approval.v1' -or
    $gate.approved -cne $true -or $gate.phase -cne $Phase -or
    $gate.qualified_main_sha -cne $ExpectedMainSha -or
    $gate.expected_event_head_sha256 -cne $ExpectedHeadSha) {
  throw 'F139_OWNER_BRIDGE_APPROVAL_FIELDS_OR_HEAD_DRIFT'
}
if ($Phase -ceq 'custody' -and $state.head_seq -ne 55) {
  throw 'F139_OWNER_CUSTODY_REQUIRES_EVENT_55'
}
if ($Phase -ceq 'transition' -and $state.head_seq -ne 56) {
  throw 'F139_OWNER_TRANSITION_REQUIRES_EVENT_56'
}
if ($Phase -ceq 'activate' -and $state.head_seq -ne 57) {
  throw 'F139_OWNER_ACTIVATION_REQUIRES_EVENT_57'
}
$cli = @('--db',$db)
if ($Phase -ceq 'custody') {
  if (-not (Test-Path -LiteralPath $key -PathType Leaf)) {
    throw 'F139_OWNER_DPAPI_KEY_MISSING'
  }
  $secure = Import-Clixml -LiteralPath $key
  if (-not ($secure -is [Security.SecureString])) {
    throw 'F139_OWNER_DPAPI_KEY_NOT_SECURESTRING'
  }
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { $env:F139_WORKER_HMAC_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
  if ($env:F139_WORKER_HMAC_KEY.Length -lt 32) {
    throw 'F139_OWNER_DPAPI_KEY_TOO_SHORT'
  }
  $cli += 'custody-original-native-split-negative'
} elseif ($Phase -ceq 'transition') {
  $specific = Join-Path $approvalDir 'transition-qualified-native.json'
  if (-not (Test-Path -LiteralPath $specific -PathType Leaf)) {
    throw 'F139_OWNER_SOURCE_APPROVAL_ABSENT'
  }
  $cli += @('transition-qualified-native','--approval',$specific)
} else {
  $specific = Join-Path $approvalDir 'activate-native.json'
  if (-not (Test-Path -LiteralPath $specific -PathType Leaf)) {
    throw 'F139_OWNER_NATIVE_APPROVAL_ABSENT'
  }
  $cli += @('activate-native','--approval',$specific)
}
try {
  Push-Location -LiteralPath $root
  try {
    & $python -B -m f139.local_controller @cli
    if ($LASTEXITCODE -ne 0) { throw 'F139_OWNER_PHASE_CLI_FAILED' }
  } finally { Pop-Location }
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
}
Write-Host "F139_OWNER_BRIDGE_PHASE=$Phase"
Write-Host 'F139_OWNER_BRIDGE_NO_NATIVE_DISPATCH=TRUE'
