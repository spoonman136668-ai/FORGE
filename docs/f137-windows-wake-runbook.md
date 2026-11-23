# F137 Windows wake / existing F136 controller — operator runbook

**Status at introduction:** draft PR only. No authorization to dispatch production science.
Keep the original `FORGE-F137-WakeProbe` Task Scheduler installation unchanged
until the exact PR head is qualified and merged under ordinary protection rules.

## Architecture / boundaries

1. Windows Task Scheduler runs in the **SYSTEM service session**, outside the
   desktop, every ten minutes. The existing proven probe's log file remains
   `%ProgramData%\\FORGE-F137-WakeProbe\\observations.jsonl`.
2. Local `scripts/f137-windows-wake.ps1` reads protected main, integrated
   run history and wake-controller history. When no explicit local config or
   credential exists it is **READ_ONLY** (zero dispatches).
3. If **both** local config and GitHub repository variable
   `FORGE_F137_WINDOWS_WAKE_ENABLED=true` are independently enabled, a
   **restricted fine-grained PAT for the FORGE repository, Actions: read/write
   only** may call `workflow_dispatch` for the **existing** F136 controller.
   It cannot directly launch the integrated research workflow.
4. The same existing F136 controller validates pinned source, owner actor,
   actual GitHub run attempt, nonce, all integrated runs and other wake runs,
   recent completion grace, daily cap, operator pause, near-cron timing,
   frozen protocol and repeat read. A permitted result dispatches at most one
   **synthetic development-only** integrated cycle.
5. The integrated workflow reports source and receipts. Neither Windows
   `workflow_dispatch` nor source-gated `workflow_run` is a genuine GitHub
   cron `schedule` event. No F125/F127/F128 scheduled scientific stage,
   protected first use, science originals, optimizer promotion, Codex or CKB
   plane may be accepted from this inlet.

**Limitation:** Concurrency plus provider run-history checks bound duplicate
opportunities; they are *not* a linearizable distributed lock with the delayed
native GitHub cron source. The qualified integrated workflow's own concurrency
serializes runs, and all non-scheduled science remains denied. Record all safe
declines rather than relaxing the frozen policy.

## Preflight before any write enablement

- Independently verify unattended Windows Task Scheduler **recurrence**:
  two rows in `observations.jsonl` with `result=OK`, zero dispatched and
  distinct timestamps about ten minutes apart; Task Scheduler exit code 0.
- Verify exact protected `main`, PR head, and green Linux/Windows regression,
  F136/F137 unit gates and PowerShell **5.1** syntax; follow standard merge
  protections. A changed PR head requires new qualification.
- The new controller must have been merged into protected main. A draft PR
  does not authorize a token, repo-variable enablement, or a modified task.
- Check user permission and GitHub Actions quotas. Only the FORGE repository
  is authorized. Avoid broad `gh auth token` or existing subscription tokens
  for SYSTEM: provision a **new** fine-grained PAT, scoped to FORGE and
  `Actions: Read and write`; `Metadata: Read` is automatic. Never paste a
  credential into chat, a source file, a GH issue, process command arguments,
  or an observation log.

## Staged source install, disabled by default (Administrator PowerShell)

After merge, **replace `<QUALIFIED_PROTECTED_SHA>`** with exact qualified
merged-main source; stop on any hash or source mismatch.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'spoonman136668-ai/FORGE'
$ref = '<QUALIFIED_PROTECTED_SHA>'
if ($ref -notmatch '^[0-9a-f]{40}$') { throw 'F137_INVALID_REF' }
$protected = (& gh api "repos/$repo/branches/main" | ConvertFrom-Json).commit.sha
if ($LASTEXITCODE -ne 0 -or $protected -cne $ref) { throw 'F137_MAIN_DRIFT' }
$root = Join-Path $env:ProgramData 'FORGE-F137-WakeProbe'
$task = Get-ScheduledTask -TaskName 'FORGE-F137-WakeProbe' -ErrorAction Stop
if ($task.Principal.UserId -notin @('SYSTEM','S-1-5-18')) {
    throw 'F137_PRINCIPAL_NOT_SYSTEM'
}
if ($task.Settings.MultipleInstances -ne 'IgnoreNew') {
    throw 'F137_TASK_SINGLE_INSTANCE_MISSING'
}
$packet = & gh api "repos/$repo/contents/scripts/f137-windows-wake.ps1?ref=$ref" |
  ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'F137_SOURCE_FETCH_FAILED' }
$source = [Text.Encoding]::UTF8.GetString(
  [Convert]::FromBase64String(($packet.content -replace '\s','')))
$path = Join-Path $root 'wake.ps1'
if (Test-Path -LiteralPath $path) { throw 'F137_WAKE_ALREADY_STAGED' }
[IO.File]::WriteAllText($path, $source, [Text.UTF8Encoding]::new($false))
$tokens = $null; $errorsFound = $null
[void][Management.Automation.Language.Parser]::ParseFile(
    $path, [ref]$tokens, [ref]$errorsFound)
if ($errorsFound.Count -ne 0) { throw 'F137_WAKE_PARSE_FAILED' }
@{schema='forge.f137.windows-wake-config.v1';enable_development_wake=$false} |
  ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $root 'wake-config.json')
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -Argument "-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$path`""
Set-ScheduledTask -TaskName 'FORGE-F137-WakeProbe' -Action $action | Out-Null
Start-ScheduledTask -TaskName 'FORGE-F137-WakeProbe'
Start-Sleep -Seconds 8
Get-ScheduledTaskInfo -TaskName 'FORGE-F137-WakeProbe' |
  Select-Object LastRunTime,LastTaskResult,NextRunTime
Get-Content (Join-Path $root 'observations.jsonl') -Tail 1
```

Expected: exit code 0, `LOCAL_DISPATCH_DISABLED`, `dispatched=false`.
This tests the new script as SYSTEM **without** any token or dispatch.

## Optional later activation (separate authorization/acceptance gate)

When the user explicitly authorizes live development-only wake after PR merge
and read-only tests, provision a new fine-grained GitHub token. In an elevated
**interactive** PowerShell session, use `Read-Host -AsSecureString` and
DPAPI `LocalMachine` to write `github-token.dpapi` into the existing
SYSTEM/Administrators-only ACL directory. **Never** use the broad existing
`gh auth token`. The SYSTEM task can decrypt locally; the key never appears
in command arguments or logs. Recheck directory and file ACLs before enabling.

Set the repo variable `FORGE_F137_WINDOWS_WAKE_ENABLED=true` using the
authorized GitHub Settings UI and then (last) set
`wake-config.json.enable_development_wake=true`. Allow the next genuine
Windows Task Scheduler tick to originate the request; do not substitute a
manual `workflow_dispatch` for the unattended acceptance. Correlate the
local `wake_nonce` with the provider F137 decision artifact and the child
integrated `workflow_dispatch` source SHA. Confirm both operating-system
proofs, no first-use, no accepted-ref mutation, correct budget and no duplicate.

**Recovery:** Disarm the local config immediately (set `enable_development_wake`
false), and set the GitHub repository variable false. Remove the fine-grained
token file and revoke the PAT if compromised. The original read-only probe
script remains at `probe.ps1` and can be restored as the Task Scheduler
action without deleting the log.

**F137 status** remains distinct:
- Windows wake acceptance: two authentic background ticks + properly sourced
  development dispatch and completion receipts; not proven by unit tests alone.
- Original F137 GitHub cron acceptance: a genuine GitHub `event=schedule`
  on the qualified merged source plus correct successor; still independent.
