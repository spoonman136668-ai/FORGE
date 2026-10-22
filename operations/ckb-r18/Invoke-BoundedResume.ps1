[CmdletBinding()]
param([switch]$Execute)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 3.0

$owner=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($owner)
if ($env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE' -or
    $env:GITHUB_REPOSITORY -cne 'spoonman136668-ai/FORGE' -or
    $env:GITHUB_REF -cne 'refs/heads/operate/ckb-r18-bounded-resume-20261022' -or
    $env:GITHUB_RUN_ATTEMPT -cne '1' -or
    $owner.Name -ine 'LINKDEADKB\camar' -or
    !$admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'CKB_R18_BOUND_RESUME_OWNER_AUTHORITY_INVALID'
}
$expectedExe='c4e314e14db5f1890e275439171cb22343581d601ba86a4bedfd2e66efe501e2'
$expectedConfig='6ff5310bf343a72c07343874f06ba9060567549d1ddbb8dd5e4c17691201967c'
$config='C:\Users\camar\GolandProjects\ckb-plane\config\autonomy.yaml'
$db='C:\Users\camar\GolandProjects\ckb-plane\state\autonomy.db'
$py=(Get-Command python.exe -ErrorAction Stop).Source
$taskName='CKB-plane Controller'
function IdentifyController {
    $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if ($task.State -ne 'Running' -or
        @($task.Actions).Count -ne 1 -or
        [string]$task.Actions[0].Arguments -notlike '*Start-R18-Controller.ps1*' -or
        [string]$task.Principal.UserId -notin @('camar','LINKDEADKB\camar')) {
        throw 'CKB_R18_EXISTING_CONTROLLER_TASK_IDENTITY_DRIFT'
    }
    $processes=@(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop)
    if ($processes.Count -ne 1 -or
        [string]::IsNullOrWhiteSpace([string]$processes[0].ExecutablePath)) {
        throw 'CKB_R18_CONTROLLER_NOT_SINGLETON'
    }
    $file=[string]$processes[0].ExecutablePath
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedExe -or
        (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedConfig) {
        throw 'CKB_R18_QUALIFIED_BINARY_OR_CONFIG_DRIFT'
    }
    return [ordered]@{exe=$file;pid=[int]$processes[0].ProcessId}
}
function QueryFrozenQueue([string]$expectedPause) {
    if (!(Test-Path -LiteralPath $db -PathType Leaf)) {throw 'CKB_R18_ORIGINAL_DB_MISSING'}
    $source=@'
import json,sqlite3,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve(strict=True)
s=sqlite3.connect("file:"+p.as_posix()+"?mode=ro",uri=True,timeout=3)
try:
 s.execute("PRAGMA query_only=ON")
 q=dict(s.execute("SELECT state,count(*) FROM queue_items GROUP BY state"))
 w=dict(s.execute("SELECT state,count(*) FROM work_orders GROUP BY state"))
 n=s.execute("SELECT COUNT(*) FROM worker_leases").fetchone()[0]
 paused=s.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]
 authority=s.execute("SELECT value FROM settings WHERE key='autonomy_authority'").fetchone()[0]
 generation=s.execute("SELECT value FROM settings WHERE key='autonomy_generation'").fetchone()[0]
 print("CKB_R18_PAUSE_STATE="+json.dumps({"queue":q,"work":w,"leases":n,"paused":paused,
     "authority":authority,"generation":generation},separators=(",",":")))
finally:s.close()
'@
    $file=Join-Path $env:RUNNER_TEMP ('ckb-r18-query-'+[guid]::NewGuid().ToString('N')+'.py')
    [IO.File]::WriteAllText($file,$source,(New-Object Text.UTF8Encoding($false)))
    try {
        $output=@(& $py -B $file $db)
        if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1 -or
            [string]$output[0] -cnotmatch '^CKB_R18_PAUSE_STATE=\{') {throw 'CKB_R18_READONLY_DB_QUERY_FAILED'}
        $state=([string]$output[0]).Substring('CKB_R18_PAUSE_STATE='.Length) | ConvertFrom-Json
    } finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
    $q=$state.queue;$w=$state.work
    if ($state.paused -cne $expectedPause -or
        $state.authority -cne 'plane' -or
        $state.generation -cne '6' -or
        [int]$state.leases -ne 0 -or
        $q.COMPLETED -ne 131 -or $q.REVIEWED -ne 70 -or
        @($q.PSObject.Properties).Count -ne 2 -or
        $w.ACCEPTED -ne 130 -or $w.BLOCKED -ne 62 -or
        $w.DRAFT -ne 2 -or $w.REJECTED_RETRYABLE -ne 4 -or
        @($w.PSObject.Properties).Count -ne 4) {
        throw 'CKB_R18_STORED_WORKLOAD_OR_AUTHORITY_CHANGED'
    }
    return $state
}
function NativeClient([string]$exe,[string]$operation) {
    $tag=[guid]::NewGuid().ToString('N')
    $out=Join-Path $env:RUNNER_TEMP ('ckb-r18-'+$tag+'.out')
    $err=Join-Path $env:RUNNER_TEMP ('ckb-r18-'+$tag+'.err')
    try {
        $client=Start-Process -FilePath $exe -ArgumentList @('controller',$operation,'--config',('"' + $config + '"')) -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err -ErrorAction Stop
        if (!$client.WaitForExit(90000)) {
            try {$client.Kill()} catch {}
            throw ('CKB_R18_'+$operation.ToUpperInvariant()+'_CLI_TIMEOUT')
        }
        if ($client.ExitCode -ne 0) {
            # Classify only known native authority-fence errors; never log
            # stderr, command environment, tokens, credentials or paths.
            $failureText=([IO.File]::ReadAllText($err)+' '+[IO.File]::ReadAllText($out))
            $classes=@(
                'WINDOWS_QUALIFICATION_REQUIRED_OR_CONFIGURATION_CHANGED',
                'QUALIFICATION_RECEIPT_MISSING','QUALIFICATION_RECEIPT_INVALID',
                'ORIGINAL_AUTHORITY_GUARD_NOT_CONFIGURED',
                'ORIGINAL_WORKFLOW_NOT_DISABLED',
                'ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS',
                'ORIGINAL_REPOSITORY_MISMATCH',
                'ORIGINAL_ARCHITECTURE_REMAINS_AUTHORITY',
                'AUTONOMY_NOT_CONFIGURED',
                'AUTHORITY_REPOSITORY_MISMATCH',
                'R4C1_NATIVE_PROOF_REQUIRED_BEFORE_CUTOVER',
                'ORIGINAL_AUTHORITY_LOCAL_PROOF_REQUIRED'
            )
            $reason='OTHER_REJECTED_BY_NATIVE_GUARD'
            foreach($candidate in $classes) {
                if ($failureText.Contains($candidate)) {$reason=$candidate;break}
            }
            throw ('CKB_R18_'+$operation.ToUpperInvariant()+'_CLI_REJECTED_'+$reason)
        }
        if ((Get-Item -LiteralPath $out).Length -gt 16777216) {throw 'CKB_R18_NATIVE_OUTPUT_EXCEEDS_BOUND'}
        $raw=[IO.File]::ReadAllText($out)
        return ConvertFrom-Json -InputObject $raw -ErrorAction Stop
    } finally {
        Remove-Item -LiteralPath $out,$err -Force -ErrorAction SilentlyContinue
    }
}
function AssertNative([string]$exe,[bool]$expectedPaused) {
    $view=NativeClient $exe 'status'
    $state=if($expectedPaused){'PAUSED'}else{'IDLE: no authorized eligible work'}
    $blockers=@($view.blockers | Where-Object {$null -ne $_})
    if ([string]$view.authority -cne 'plane' -or
        [string]$view.generation -cne '6' -or
        $view.heartbeat_stale -ne $false -or
        [string]::IsNullOrWhiteSpace([string]$view.heartbeat_at) -or
        $view.paused -ne $expectedPaused -or
        [string]$view.controller_status -cne $state -or
        $blockers.Count -ne 0) {
        throw 'CKB_R18_NATIVE_STATUS_NOT_FROZEN_EXPECTED_STATE'
    }
    return $view
}
$before=IdentifyController
[void](QueryFrozenQueue 'true')
[void](AssertNative $before.exe $true)
Write-Host 'CKB_R18_EXISTING_OWNER_BINARY_STATE_AND_QUEUE=PASS'
if (!$Execute) {
    Write-Host 'CKB_R18_PRECHECK_ONLY=PASS'
    Write-Host 'CKB_R18_DISPATCH_RESUMED=FALSE'
    return
}
$attempted=$false
try {
    $attempted=$true
    [void](NativeClient $before.exe 'resume')
    [void](QueryFrozenQueue 'false')
    [void](AssertNative $before.exe $false)
    $after=IdentifyController
    if ($after.pid -ne $before.pid -or $after.exe -ine $before.exe) {
        throw 'CKB_R18_PROCESS_CHANGED_DURING_BOUNDED_RESUME'
    }
    Write-Host 'CKB_R18_OWNER_APPROVED_NATIVE_RESUME=PASS'
    Write-Host 'CKB_R18_NO_ELIGIBLE_QUEUE_OR_WORKER_LEASE=PASS'
    Write-Host 'CKB_R18_CONTROLLER_SINGLETON_AND_HEARTBEAT=PASS'
    Write-Host 'CKB_R18_NO_NEW_WORK_DISPATCHED=PASS'
} catch {
    $originalFailure=$_.Exception.Message
    if ($attempted) {
        try {
            [void](NativeClient $before.exe 'pause')
            [void](QueryFrozenQueue 'true')
            [void](AssertNative $before.exe $true)
            $after=IdentifyController
            if ($after.pid -ne $before.pid) {throw 'CKB_R18_CONTROLLER_IDENTITY_CHANGED'}
            Write-Host 'CKB_R18_AUTOMATIC_OPERATOR_PAUSE_RESTORED=PASS'
        } catch {
            throw ('CKB_R18_BOUND_RESUME_FAILED_MANUAL_PAUSE_CUSTODY_REQUIRED: '+$originalFailure)
        }
    }
    throw ('CKB_R18_BOUND_RESUME_NOT_ACCEPTED: '+$originalFailure)
}
