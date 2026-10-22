[CmdletBinding()]
param([switch]$Execute)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 3.0
$wid=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($wid)
if ($env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE' -or
    $env:GITHUB_REPOSITORY -cne 'spoonman136668-ai/FORGE' -or
    $env:GITHUB_REF -cne 'refs/heads/operate/ckb-r18-native-requalify-20261022' -or
    $env:GITHUB_RUN_ATTEMPT -cne '1' -or
    $wid.Name -ine 'LINKDEADKB\camar' -or
    !$admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'CKB_R18_REQUAL_OWNER_AUTHORITY_DRIFT'
}
$root='C:\Users\camar\GolandProjects\ckb-plane'
$db=Join-Path $root 'state\autonomy.db'
$config=Join-Path $root 'config\autonomy.yaml'
$taskName='CKB-plane Controller'
$expectedExe='c4e314e14db5f1890e275439171cb22343581d601ba86a4bedfd2e66efe501e2'
$expectedCfg='6ff5310bf343a72c07343874f06ba9060567549d1ddbb8dd5e4c17691201967c'
$expectedAction='cb83905cfa4aa7e99683038160448802bdaf8c602c387f575fa8b1bf0ffad29c'
$backupBase='C:\ProgramData\CKBR\cutover'
$py=(Get-Command python.exe -ErrorAction Stop).Source
function CurrentController {
    $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if ($task.State -ne 'Running' -or @($task.Actions).Count -ne 1 -or
        [string]$task.Principal.UserId -notin @('camar','LINKDEADKB\camar') -or
        [string]$task.Actions[0].Arguments -notlike '*Start-R18-Controller.ps1*') {
        throw 'CKB_R18_REQUAL_TASK_OWNER_OR_RELEASE_DRIFT'
    }
    $args=[string]$task.Actions[0].Arguments
    $digest=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($args)))
    if ($digest.ToLowerInvariant() -cne $expectedAction) {throw 'CKB_R18_REQUAL_TASK_ACTION_DRIFT'}
    $procs=@(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop)
    if ($procs.Count -ne 1 -or
        [string]::IsNullOrWhiteSpace([string]$procs[0].ExecutablePath)) {
        throw 'CKB_R18_REQUAL_NOT_SINGLETON'
    }
    $exe=[string]$procs[0].ExecutablePath
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedExe -or
        (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedCfg) {
        throw 'CKB_R18_REQUAL_BIN_OR_CFG_CHANGED'
    }
    return [ordered]@{exe=$exe;pid=[int]$procs[0].ProcessId;actionDigest=$digest.ToLowerInvariant()}
}
function NativeClient([string]$exe,[string]$verb,[int]$timeoutMs=75000) {
    $tag=[guid]::NewGuid().ToString('N')
    $stdout=Join-Path $env:RUNNER_TEMP ('ckb-native-'+$tag+'.out')
    $stderr=Join-Path $env:RUNNER_TEMP ('ckb-native-'+$tag+'.err')
    try {
        $ps=Start-Process -FilePath $exe -ArgumentList @('controller',$verb,'--config',('"' + $config + '"')) -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr -ErrorAction Stop
        if (!$ps.WaitForExit($timeoutMs)) {
            try {$ps.Kill()} catch {}
            throw ('CKB_R18_'+$verb.ToUpperInvariant()+'_TIMEOUT')
        }
        if ($ps.ExitCode -ne 0) {
            # Preserve rejection details privately in the qualification log
            # only as a fixed code, not as user-work or credential text.
            $log=([IO.File]::ReadAllText($stderr)+' '+[IO.File]::ReadAllText($stdout))
            $mark='OTHER_NATIVE_REJECTION'
            foreach ($choice in @('SERVICE_LOCKED','CONTROLLER_PID_LIVE_OR_UNVERIFIED',
                'WINDOWS_SANDBOX_QUALIFICATION_FAILED','CONFIGURE_SANDBOX_SYNTAX_FIRST',
                'RECOVERY_WAITING_FOR_SUPERVISOR','NATIVE_WINDOWS_QUALIFICATION_REQUIRED',
                'QUALIFICATION_RECEIPT_INVALID','REAL_ENVIRONMENT_PREFLIGHT_FAILED')) {
                if ($log.Contains($choice)) {$mark=$choice;break}
            }
            throw ('CKB_R18_'+$verb.ToUpperInvariant()+'_FAILED_'+$mark)
        }
        if ((Get-Item -LiteralPath $stdout).Length -gt 16777216) {
            throw 'CKB_R18_NATIVE_JSON_OVERSIZED'
        }
        $json=[IO.File]::ReadAllText($stdout)
        return ConvertFrom-Json -InputObject $json -ErrorAction Stop
    } finally {
        Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue
    }
}
function CheckFrozenWorkload([string]$expectedPause) {
    $program=@'
import sqlite3,sys,json
from pathlib import Path
p=Path(sys.argv[1]).resolve(strict=True)
s=sqlite3.connect("file:"+p.as_posix()+"?mode=ro",uri=True,timeout=3)
try:
 s.execute("PRAGMA query_only=ON")
 q=dict(s.execute("SELECT state,count(*) FROM queue_items GROUP BY state"))
 w=dict(s.execute("SELECT state,count(*) FROM work_orders GROUP BY state"))
 leases=s.execute("SELECT COUNT(*) FROM worker_leases").fetchone()[0]
 vals=dict(s.execute("SELECT key,value FROM settings WHERE key IN ('paused','autonomy_authority','autonomy_generation')"))
 result={"queue":q,"work":w,"leases":leases,"paused":vals.get("paused"),
  "authority":vals.get("autonomy_authority"),"generation":vals.get("autonomy_generation")}
 print(json.dumps(result,separators=(",",":")))
finally:s.close()
'@
    $file=Join-Path $env:RUNNER_TEMP ('ckb-qual-sql-'+[guid]::NewGuid().ToString('N')+'.py')
    [IO.File]::WriteAllText($file,$program,(New-Object Text.UTF8Encoding($false)))
    try {
        $raw=@(& $py -B $file $db)
        if ($LASTEXITCODE -ne 0 -or $raw.Count -ne 1) {throw 'CKB_R18_READONLY_STATE_QUERY_FAILED'}
        $state=[string]$raw[0]|ConvertFrom-Json -ErrorAction Stop
    } finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
    if ($state.paused -cne $expectedPause -or
        $state.authority -cne 'plane' -or $state.generation -cne '6' -or
        $state.leases -ne 0 -or
        $state.queue.COMPLETED -ne 131 -or $state.queue.REVIEWED -ne 70 -or
        @($state.queue.PSObject.Properties).Count -ne 2 -or
        $state.work.ACCEPTED -ne 130 -or $state.work.BLOCKED -ne 62 -or
        $state.work.DRAFT -ne 2 -or $state.work.REJECTED_RETRYABLE -ne 4 -or
        @($state.work.PSObject.Properties).Count -ne 4) {
        throw 'CKB_R18_QUAL_WORKLOAD_CHANGED_OR_NOT_QUIESCENT'
    }
    return $state
}
function AssertPausedHealth([string]$exe) {
    $s=NativeClient $exe 'status'
    if ([string]$s.authority -cne 'plane' -or
        [string]$s.generation -cne '6' -or
        $s.paused -ne $true -or
        [string]$s.controller_status -cne 'PAUSED' -or
        $s.heartbeat_stale -ne $false -or
        @($s.blockers|Where-Object {$null -ne $_}).Count -ne 0) {
        throw 'CKB_R18_REQUAL_CONTROLLER_NOT_HEALTHY_PAUSED'
    }
}
function WaitZero {
    for($i=0;$i -lt 90;$i++) {
        if(@(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop).Count -eq 0){return $true}
        Start-Sleep -Milliseconds 500
    }
    return $false
}
function WaitSameRelease([string]$exe) {
    for($i=0;$i -lt 120;$i++) {
        $ps=@(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop)
        if($ps.Count -eq 1 -and [string]$ps[0].ExecutablePath -ieq $exe){return $true}
        if($ps.Count -gt 1){throw 'CKB_R18_REQUAL_CONCURRENT_CONTROLLERS'}
        Start-Sleep -Milliseconds 500
    }
    return $false
}
$original=CurrentController
[void](CheckFrozenWorkload 'true')
AssertPausedHealth $original.exe
Write-Host 'CKB_R18_NATIVE_QUAL_OWNER_CONFIG_AND_FROZEN_QUEUE=PASS'
if (!$Execute) {
    Write-Host 'CKB_R18_REQUALIFY_PREFLIGHT_ONLY=PASS'
    Write-Host 'CKB_R18_LIVE_CONTROLLER_STOPPED=FALSE'
    return
}
$backup=Join-Path $backupBase ('R18-EXACT-NATIVE-QUAL-'+$env:GITHUB_RUN_ID)
if(Test-Path -LiteralPath $backup){throw 'CKB_R18_BACKUP_DESTINATION_EXISTS'}
New-Item -ItemType Directory -Path $backup -ErrorAction Stop | Out-Null
$nativeStopped=$false
$snapshotted=$false
try {
    # Native IPC shutdown, not Task Scheduler Stop, is the proven method for
    # this detached process. Do not force-kill the controller.
    [void](NativeClient $original.exe 'stop')
    if(!(WaitZero)){throw 'CKB_R18_NATIVE_CONTROLLER_NOT_STOPPED'}
    $nativeStopped=$true
    $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if($task.State -eq 'Running'){
        Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
    } elseif($task.State -ne 'Ready'){
        throw 'CKB_R18_QUAL_TASK_NOT_READY_AFTER_NATIVE_STOP'
    }
    if(!(WaitZero)){throw 'CKB_R18_QUAL_OLD_CONTROLLER_RESTARTED'}
    # Snapshot original SQLite and WAL/SHM only after all controller locks
    # are released. Rollback will restore exact database preimages.
    foreach($suf in @('','-wal','-shm')) {
        $from=$db+$suf
        if(Test-Path -LiteralPath $from -PathType Leaf) {
            Copy-Item -LiteralPath $from -Destination (Join-Path $backup ('autonomy.db'+$suf)) -ErrorAction Stop
        }
    }
    if(!(Test-Path -LiteralPath (Join-Path $backup 'autonomy.db') -PathType Leaf)){
        throw 'CKB_R18_QUAL_DB_SNAPSHOT_MISSING'
    }
    Copy-Item -LiteralPath $config -Destination (Join-Path $backup 'original-autonomy.yaml') -ErrorAction Stop
    $snapshotted=$true
    # This native command genuinely runs the Windows sandbox test and updates
    # its own digest/receipt only AFTER passing. No synthetic digest writes.
    $result=NativeClient $original.exe 'qualify' 360000
    if ($result.schema -cne 'ckb-plane.windows-qualification.v1' -or
        $result.passed -ne $true -or
        [string]::IsNullOrWhiteSpace([string]$result.config_and_tool_digest)) {
        throw 'CKB_R18_NATIVE_WINDOWS_QUALIFICATION_NOT_PASSED'
    }
    [void](CheckFrozenWorkload 'true')
    # Verify the native qualification's durable receipt points to the same
    # proven digest. Never fabricate or edit an authority setting.
    $program=@'
import sqlite3,json,sys
from pathlib import Path
d=Path(sys.argv[1]).resolve(strict=True)
s=sqlite3.connect("file:"+d.as_posix()+"?mode=ro",uri=True)
try:
 val=dict(s.execute("SELECT key,value FROM settings WHERE key IN ('qualification_digest','qualification_receipt')"))
 r=Path(val["qualification_receipt"]).resolve(strict=True)
 if r.stat().st_size>65536:raise ValueError("CKB_QUAL_RECEIPT_LARGE")
 obj=json.loads(r.read_text('utf-8'))
 result={"passed":obj.get("passed") is True,
   "digest_equal":obj.get("config_and_tool_digest")==val["qualification_digest"],
   "digest":val["qualification_digest"]}
 print(json.dumps(result,separators=(",",":")))
finally:s.close()
'@
    $receiptScript=Join-Path $env:RUNNER_TEMP ('R18QualVerify-'+$env:GITHUB_RUN_ID+'.py')
    [IO.File]::WriteAllText($receiptScript,$program,(New-Object Text.UTF8Encoding($false)))
    try {
        $out=@(& $py -B $receiptScript $db)
        if($LASTEXITCODE -ne 0 -or $out.Count -ne 1) {
            throw 'CKB_R18_NATIVE_RECEIPT_NOT_READABLE'
        }
        $checked=[string]$out[0]|ConvertFrom-Json -ErrorAction Stop
    } finally {
        Remove-Item -LiteralPath $receiptScript -Force -ErrorAction SilentlyContinue
    }
    if (!$checked.passed -or !$checked.digest_equal -or
        $checked.digest -cne $result.config_and_tool_digest) {
        throw 'CKB_R18_NATIVE_QUALIFIED_RECEIPT_INTEGRITY_FAILED'
    }
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if(!(WaitSameRelease $original.exe)){throw 'CKB_R18_QUALIFIED_CONTROLLER_RESTART_UNVERIFIED'}
    $task=CurrentController
    if($task.pid -eq $original.pid){throw 'CKB_R18_RESTART_PID_NOT_NEW'}
    # The same qualified executable must now pass its native status while
    # remaining intentionally paused until the separate native resume gate.
    [void](CheckFrozenWorkload 'true')
    AssertPausedHealth $original.exe
    if ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedCfg){
        throw 'CKB_R18_QUALIFICATION_CHANGED_CONFIG_BYTES'
    }
    Write-Host 'CKB_R18_GENUINE_NATIVE_WINDOWS_SANDBOX_QUALIFICATION=PASS'
    Write-Host 'CKB_R18_QUALIFICATION_RECEIPT_AND_CONTRACT_MATCH=PASS'
    Write-Host 'CKB_R18_RESTARTED_ORIGINAL_R18_SINGLETON=PASS'
    Write-Host 'CKB_R18_AUTHORITY_GENERATION_6_PAUSED=PASS'
    Write-Host 'CKB_R18_DISPATCH_NOT_ENABLED=TRUE'
} catch {
    $reason=$_.Exception.Message
    if($nativeStopped){
        try {
            $ps=@(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop)
            if($ps.Count -gt 1){throw 'CKB_R18_QUAL_ROLLBACK_CONCURRENT_PROCESSES'}
            if($ps.Count -eq 1){
                if([string]$ps[0].ExecutablePath -ine $original.exe){
                    throw 'CKB_R18_QUAL_ROLLBACK_UNKNOWN_RELEASE_PROCESS'
                }
                [void](NativeClient $original.exe 'stop')
            }
            if(!(WaitZero)){throw 'CKB_R18_QUAL_ROLLBACK_CONTROLLER_STILL_RUNNING'}
            $task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
            if($task.State -eq 'Running') {
                Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            }
            if($snapshotted){
                foreach($suf in @('','-wal','-shm')){
                    $target=$db+$suf
                    $backupFile=Join-Path $backup ('autonomy.db'+$suf)
                    if(Test-Path -LiteralPath $target -PathType Leaf){
                        Remove-Item -LiteralPath $target -Force -ErrorAction Stop
                    }
                    if(Test-Path -LiteralPath $backupFile -PathType Leaf){
                        Copy-Item -LiteralPath $backupFile -Destination $target -ErrorAction Stop
                    }
                }
            }
            Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
            if(!(WaitSameRelease $original.exe)) {throw 'CKB_R18_QUAL_ROLLBACK_RESTART_FAILED'}
            AssertPausedHealth $original.exe
            Write-Host 'CKB_R18_ORIGINAL_R18_PAUSED_ROLLBACK=PASS'
        } catch {
            throw ('CKB_R18_QUAL_ROLLBACK_MANUAL_CUSTODY_REQUIRED: '+$reason)
        }
    }
    throw ('CKB_R18_EXACT_NATIVE_QUALIFICATION_NOT_ACCEPTED: '+$reason)
}
