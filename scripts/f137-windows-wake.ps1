# F137 Windows SYSTEM wake for the EXISTING F136 development controller.
# A read-only probe unless a separately provisioned local config explicitly
# enables it. It cannot create genuine GitHub scheduled or scientific evidence.
# No Codex, paid API, CKB-plane, window, browser, or prompts.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:ProgramData 'FORGE-F137-WakeProbe'
$log = Join-Path $root 'observations.jsonl'
$configPath = Join-Path $root 'wake-config.json'
$secretPath = Join-Path $root 'github-token.dpapi'
$base = 'https://api.github.com/repos/spoonman136668-ai/FORGE'
$headers = @{
    'User-Agent' = 'FORGE-F137-Windows-Wake'
    'Accept' = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$now = [DateTimeOffset]::UtcNow
$record = [ordered]@{
    utc = $now.ToString('o')
    schema = 'forge.f137.windows-wake-observation.v1'
    mode = 'READ_ONLY'
    result = 'UNKNOWN'
    dispatched = $false
}
function Read-Github([string]$path) {
    Invoke-RestMethod -Uri ($base + $path) -Headers $headers -TimeoutSec 30
}
function Age-Minutes([object]$date) {
    if (-not $date) { throw 'F137_API_TIMESTAMP_MISSING' }
    return ($now - [DateTimeOffset]::Parse([string]$date)).TotalMinutes
}
try {
    $branch = Read-Github '/branches/main'
    $main = [string]$branch.commit.sha
    if ($main -cnotmatch '^[a-f0-9]{40}$') { throw 'F137_BAD_PROTECTED_SHA' }
    $record.main_sha = $main

    # Keep the original SYSTEM-safe scheduler observation functionality.
    $scheduled = Read-Github '/actions/runs?event=schedule&per_page=10'
    $record.scheduled_run_count = $scheduled.total_count
    $latestSchedule = @($scheduled.workflow_runs | Where-Object { $_ }) |
        Select-Object -First 1
    if ($latestSchedule) {
        $record.latest_scheduled_id = $latestSchedule.id
        $record.latest_scheduled_utc = $latestSchedule.created_at
    }

    # F136's authoritative checks are repeated inside the GitHub-hosted
    # controller. Local checks suppress unnecessary API writes and collisions.
    $recent = Read-Github '/actions/workflows/forge-integrated-synthetic-cycle.yml/runs?branch=main&per_page=20'
    $wakeHistory = Read-Github '/actions/workflows/forge-development-succession.yml/runs?branch=main&event=workflow_dispatch&per_page=20'
    $rows = @($recent.workflow_runs | Where-Object { $_ })
    $record.recent_integrated_count = $recent.total_count
    $reasons = [System.Collections.Generic.List[string]]::new()
    if ($rows.Count -eq 0) { $reasons.Add('NO_INTEGRATED_HISTORY') }
    foreach ($run in $rows) {
        if ([string]$run.head_branch -cne 'main') { throw 'F137_NONMAIN_HISTORY' }
        if ($run.status -ne 'completed') { $reasons.Add('ACTIVE_INTEGRATED_RUN'); break }
        if ((Age-Minutes $run.created_at) -lt 9) {
            $reasons.Add('RECENT_INTEGRATED_RUN')
            break
        }
        if ((Age-Minutes $run.updated_at) -lt 5) {
            $reasons.Add('RECENT_CONTROLLER_GRACE')
            break
        }
    }
    foreach ($wake in @($wakeHistory.workflow_runs | Where-Object { $_ })) {
        if ((Age-Minutes $wake.created_at) -lt 10) {
            $reasons.Add('RECENT_WAKE_REQUEST')
            break
        }
    }

    # PowerShell's % preserves a negative dividend. Normalize to the current
    # ten-minute interval before computing the next :07/:17/... slot.
    $secondsIntoInterval = (($now.Minute % 10) * 60) + $now.Second
    $seconds = (420 - $secondsIntoInterval + 600) % 600
    if ($seconds -le 120) { $reasons.Add('FALLBACK_SLOT_IMMINENT') }

    # No config/no credential means monitoring only. Never silently switch
    # to write mode, and never use the user's broad cached gh CLI token.
    $enabled = $false
    if (Test-Path -LiteralPath $configPath) {
        $cfg = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        $enabled = ($cfg.schema -ceq 'forge.f137.windows-wake-config.v1' -and
                    $cfg.enable_development_wake -ceq $true)
    }
    if (-not $enabled) {
        $record.result = 'OK'
        $record.reason = 'LOCAL_DISPATCH_DISABLED'
    }
    elseif ($reasons.Count -gt 0) {
        $record.mode = 'WINDOWS_WAKE'
        $record.result = 'SKIP'
        $record.reason = ($reasons | Select-Object -Unique) -join ','
    }
    else {
        $record.mode = 'WINDOWS_WAKE'
        if (-not (Test-Path -LiteralPath $secretPath)) {
            throw 'F137_RESTRICTED_CREDENTIAL_MISSING'
        }
        $cipher = [IO.File]::ReadAllBytes($secretPath)
        Add-Type -AssemblyName System.Security -ErrorAction Stop
        $bytes = [Security.Cryptography.ProtectedData]::Unprotect(
            $cipher, $null,
            [Security.Cryptography.DataProtectionScope]::LocalMachine)
        try {
            $token = [Text.Encoding]::UTF8.GetString($bytes)
            if ([string]::IsNullOrWhiteSpace($token)) {
                throw 'F137_RESTRICTED_CREDENTIAL_EMPTY'
            }
            $nonce = [Guid]::NewGuid().ToString('N')
            $body = @{
                ref = 'main'
                inputs = @{
                    origin = 'f137-windows-wake'
                    source_sha = $main
                    wake_nonce = $nonce
                }
            } | ConvertTo-Json -Depth 4 -Compress
            $auth = @{}
            foreach ($key in $headers.Keys) { $auth[$key] = $headers[$key] }
            $auth['Authorization'] = 'Bearer ' + $token
            # This only asks an existing F136 workflow to make its own
            # separate guarded decision. It does not dispatch science.
            Invoke-RestMethod -Uri (
                $base + '/actions/workflows/forge-development-succession.yml/dispatches'
            ) -Method Post -Headers $auth -ContentType 'application/json' `
              -Body $body -TimeoutSec 30 | Out-Null
            $record.dispatched = $true
            $record.wake_nonce = $nonce
            $record.result = 'REQUEST_ACCEPTED_PENDING_SOURCE_GATES'
            $record.reason = 'CONTROLLER_WILL_REVALIDATE'
        }
        finally {
            [Array]::Clear($bytes, 0, $bytes.Length)
            $token = $null
        }
    }
}
catch {
    $record.result = 'ERROR'
    $record.error = $_.Exception.Message
}
# The log is append-only and never includes the GitHub credential.
$record | ConvertTo-Json -Depth 4 -Compress |
    Add-Content -LiteralPath $log -Encoding UTF8
if ($record.result -eq 'ERROR') { exit 1 }
exit 0
